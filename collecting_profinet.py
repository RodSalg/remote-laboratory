import snap7
from snap7.util import get_bool
from snap7.snap7types import *
import threading
import time
from src.db_dao import RemoteLaboratoryDAO
import csv
import os
import json

def connect_to_plc(plc_ip: str, rack: int, slot: int) -> snap7.client.Client:
    try:
        plc = snap7.client.Client()
        plc.connect(plc_ip, rack, slot)
        if plc.get_connected():
            print(f"Conectado com sucesso ao PLC: {plc_ip} (rack={rack}, slot={slot})")
            return plc
        else:
            print(f"Falha na conexão com o PLC: {plc_ip}")
            return None
    except Exception as e:
        print(f"Erro ao conectar ao PLC {plc_ip}: {e}")
        return None

def convert_data(step: list) -> int:
    fator_multiplicativo = 1
    resultado = 0
    for elemento in reversed(step):
        if elemento:
            resultado += fator_multiplicativo
        fator_multiplicativo *= 2
    return resultado

def get_step_list(byte, num_bits):
    step_data = []
    for bit_index in range(num_bits):
        bit_val = get_bool(byte, 0, bit_index)
        step_data.append(bit_val)
    return step_data

def generate_IOs(num_inputs: int, num_outputs: int) -> list:
    IOs = []
    for i in range(1, num_inputs + 1):
        IOs.append(f'in{i}')
    for i in range(1, num_outputs + 1):
        IOs.append(f'out{i}')
    return IOs

def save_data(experiment_number, byte, IOs, cont, txt_filename, csv_filename, experiment_name):
    try:
        step = get_step_list(byte, len(IOs))
        banco = RemoteLaboratoryDAO()
        timestamp = time.time()
        valor_do_passo = convert_data(step)

        step_json = json.dumps(step)

        print(f"[save_data] Inserindo dados: experiment={experiment_number}, passo={cont}, valor={valor_do_passo}")
        banco.insert_data_into_database(experiment_number, cont, step_json, valor_do_passo, timestamp, experiment_name)

        with open(txt_filename, 'a') as txt_file:
            txt_file.write(f"IOs: {IOs}\nPasso{cont}: {step} | Valor do passo: {valor_do_passo} | timestamp: {timestamp}\n")
            txt_file.flush()

        file_exists = os.path.isfile(csv_filename)
        with open(csv_filename, 'a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(['Passo', 'Step', 'Valor do Passo', 'Timestamp'])
            writer.writerow([cont, step, valor_do_passo, timestamp])

    except Exception as e:
        print(f"[save_data] Erro ao salvar dados: {e}")

def save_previous_state(experiment_number, byte, IOs, cont, txt_filename, csv_filename, experiment_name, duration):
    try:
        step = get_step_list(byte, len(IOs))
        banco = RemoteLaboratoryDAO()
        timestamp = time.time()
        valor_do_passo = convert_data(step)

        step_json = json.dumps(step)

        print(f"[save_previous_state] Salvando estado anterior: passo={cont}, Duracao={duration:.3f}s")

        banco.insert_data_with_duration(experiment_number, cont, step_json, valor_do_passo, timestamp, experiment_name, duration)

        with open(txt_filename, 'a') as txt_file:
            txt_file.write(f"IOs: {IOs}\nPasso{cont}: {step} | Valor do passo: {valor_do_passo} | Duracao (s): {duration:.3f} | timestamp: {timestamp}\n")
            txt_file.flush()

        file_exists = os.path.isfile(csv_filename)
        with open(csv_filename, 'a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(['Passo', 'Step', 'Valor do Passo', 'Duracao (s)', 'Timestamp'])
            writer.writerow([cont, step, valor_do_passo, duration, timestamp])

    except Exception as e:
        print(f"[save_previous_state] Erro ao salvar estado anterior: {e}")

def check_and_create_new_version(base_filename):
    version = 1
    txt_filename = f"{base_filename}.txt"
    csv_filename = f"{base_filename}.csv"

    while os.path.exists(txt_filename) or os.path.exists(csv_filename):
        version += 1
        txt_filename = f"{base_filename}_v{version}.txt"
        csv_filename = f"{base_filename}_v{version}.csv"

    return txt_filename, csv_filename

def monitor_plc(plc: snap7.client.Client, db_number: int, byte_index: int, IOs: list, experiment_name: str):
    banco = RemoteLaboratoryDAO()
    try:
        experiment_number = banco.get_last_experiment_id() + 1
        print(f"[monitor_plc] Usando experiment_number = {experiment_number}")
    except Exception as e:
        print(f"[monitor_plc] Erro ao pegar last_experiment_id: {e}")
        print("Experiment number = 1\n")
        experiment_number = 1

    txt_filename, csv_filename = check_and_create_new_version(f'{experiment_name}_{experiment_number}_')

    contador = 0
    old_bits = None

    tempo_limite = 30
    start_time = time.time()
    estado_inicio_time = None

    while True:
        data = plc.db_read(db_number, byte_index, 1)
        byte = bytearray(data)
        tempo_atual = time.time()

        current_bits = get_step_list(byte, len(IOs))

        if old_bits != current_bits:
            if old_bits is not None:
                duracao_estado = tempo_atual - estado_inicio_time
                try:
                    thSavePrev = threading.Thread(
                        target=save_previous_state,
                        args=(
                            experiment_number,
                            byte,
                            IOs,
                            contador - 1,
                            txt_filename,
                            csv_filename,
                            experiment_name,
                            duracao_estado
                        )
                    )
                    thSavePrev.start()
                except Exception as e:
                    print(f"[monitor_plc] Erro em save_previous_state: {e}")

            estado_inicio_time = tempo_atual

            # try:
            #     thSave = threading.Thread(
            #         target=save_data,
            #         args=(experiment_number, byte, IOs, contador, txt_filename, csv_filename, experiment_name)
            #     )
            #     thSave.start()
            # except Exception as e:
            #     print(f"[monitor_plc] Erro ao iniciar thread save_data: {e}")

            old_bits = current_bits
            contador += 1
            start_time = tempo_atual

        tempo_final = time.time()
        if (tempo_final - start_time) > tempo_limite:
            print("[monitor_plc] Tempo limite atingido, finalizando monitoramento.")
            if old_bits is not None and estado_inicio_time is not None:
                duracao_estado = tempo_final - estado_inicio_time
                try:
                    save_previous_state(
                        experiment_number,
                        byte,
                        IOs,
                        contador - 1,
                        txt_filename,
                        csv_filename,
                        experiment_name,
                        duracao_estado
                    )
                except Exception as e:
                    print(f"[monitor_plc] Erro ao salvar último estado: {e}")
            break

    print(f"[monitor_plc] Duracao total: {time.time() - start_time:.3f}s")
    print(f"[monitor_plc] Total de passos registrados: {contador}")

    try:
        last_experiment_id = banco.get_last_experiment_id()
        pulse_trains = banco.get_pulse_values_by_experiment(last_experiment_id)
        pulse_trains_str = "[" + ",".join(map(str, pulse_trains)) + "]"

        print('Trens de pulsos para serem cadastrados:')
        print(pulse_trains_str)

        banco.insert_pattern(experiment_number, pulse_trains_str)
        print('Trem de pulso inserido no banco!')
        print(f'Experimento: {experiment_number}')

    except Exception as e:
        print(f"[monitor_plc] Erro ao inserir o trem de pulso no banco: {e}")

    exit(1)

if __name__ == '__main__':
    banco = RemoteLaboratoryDAO()
    plants = banco.list_plant_configs()

    if not plants:
        print("Nenhuma planta cadastrada encontrada. Encerrando.")
        exit(1)

    print("Plantas cadastradas disponíveis:")
    for idx, plant in enumerate(plants, 1):
        print(f"{idx}. {plant}")

    while True:
        try:
            escolha = int(input("Digite o número da planta que deseja monitorar: "))
            if 1 <= escolha <= len(plants):
                experiment_name = plants[escolha - 1]
                print(f"Você escolheu o experimento: {experiment_name}")
                break
            else:
                print("Número inválido. Tente novamente.")
        except ValueError:
            print("Entrada inválida. Digite um número.")

    config = banco.get_plant_config(experiment_name)

    if config is None:
        print("Configuração não encontrada, encerrando.")
        exit(1)

    plc_ip = config['ip_profinet']
    rack = config['rack_profinet']
    slot = config['slot_profinet']

    db_number = config['db_number_profinet']

    num_inputs = config['num_of_inputs']
    num_outputs = config['num_of_outputs']

    IOs = generate_IOs(num_inputs, num_outputs)

    if len(IOs) > 8:
        print(f"Erro: número de IOs ({len(IOs)}) maior que 8. Encerrando aplicação.")
        exit(1)

    print(f"IOs configurados: {IOs}")

    while True:
        magFront = connect_to_plc(plc_ip, rack, slot)
        if magFront:
            print('PLC conectado!')
            byte_index = 0
            try:
                monitor_plc(magFront, db_number=db_number, byte_index=byte_index, IOs=IOs, experiment_name=experiment_name)
            except Exception as e:
                print(f'[IP: {plc_ip}] Erro ao tentar coletar dados do PLC. Ocorreu o seguinte erro: {e}\n\n')
                time.sleep(5)
            magFront.disconnect()
        else:
            print("Não foi possível conectar ao PLC\n\n")
            time.sleep(5)
