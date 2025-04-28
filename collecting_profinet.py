import snap7
from snap7.util import get_bool
from snap7.snap7types import *
import threading
from datetime import datetime
import time
from src.db_dao import RemoteLaboratoryDAO
import csv
import os


def connect_to_plc(plc_ip: str, rack: int, slot: int) -> snap7.client.Client:
    try:
        plc = snap7.client.Client()
        plc.connect(plc_ip, rack, slot)
        if plc.get_connected():
            print("Conectado com sucesso ao PLC")
            return plc
        else:
            print("Falha na conexão com o PLC")
            return None
    except Exception as e:
        print(f"Erro ao conectar ao PLC: {e}")
        return None

def convert_data(step: list) -> int:
    fator_multiplicativo = 1
    resultado = 0
    for elemento in reversed(step):
        if elemento:
            resultado += fator_multiplicativo
        fator_multiplicativo *= 2
    return resultado



# def save_data(step_bits: list):
#     def process_and_save():
#         passo = convert_data(step_bits)
#         timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         with open("dados_plc.txt", "a") as file:
#             file.write(f"{timestamp} - Trem de Pulso: {step_bits} | Passo: {passo}\n")
#         print(f"Salvo: Passo {passo} a partir do trem de pulso {step_bits}")
#     threading.Thread(target=process_and_save).start()


def get_step_list(byte):
    step_data = []

    for bit_index in range(8):

        bit_val = get_bool(byte, 0, bit_index)
        step_data.append(bit_val)

    return step_data

def save_data(experiment_number, byte, input_values, cont, txt_filename, csv_filename):
    
    step = get_step_list(byte)
    banco = RemoteLaboratoryDAO()
    
    timestamp = time.time()

    valor_do_passo = convert_data(step)

    banco.insert_data_into_database(experiment_number, cont, step, valor_do_passo, timestamp, 'magFront')
    
    with open(txt_filename, 'a') as txt_file:
    
        txt_file.write(f"IOs: {input_values}\nPasso{cont}: {step} | Valor do passo: {valor_do_passo} | timestamp: {timestamp}\n")
        txt_file.flush()
    
    file_exists = os.path.isfile(csv_filename)

    with open(csv_filename, 'a', newline='') as csv_file:
        
        writer = csv.writer(csv_file)
        
        if not file_exists:
            
            writer.writerow(['Passo', 'Step', 'Valor do Passo', 'Timestamp'])

        writer.writerow([cont, step, valor_do_passo, timestamp])

def check_and_create_new_version(base_filename):
    
    version = 1
    
    txt_filename = f"{base_filename}_v{version}.txt"
    csv_filename = f"{base_filename}_v{version}.csv"
    
    while os.path.exists(txt_filename) or os.path.exists(csv_filename):
    
        version += 1
        txt_filename = f"{base_filename}_v{version}.txt"
        csv_filename = f"{base_filename}_v{version}.csv"
    
    return txt_filename, csv_filename

def monitor_plc(plc: snap7.client.Client, db_number: int, byte_index: int):
    banco = RemoteLaboratoryDAO()
    # ultimo_trem_de_pulso = None

    
    try:
        experiment_number = banco.get_last_experiment_id() + 1

    except:
        experiment_number = 1


    txt_filename, csv_filename = check_and_create_new_version(f'steps_exp_number_{experiment_number}_')
    

    contador = 0
    sensors = ['in1', 'in2', 'in3', 'in4', 'in5',]

    old_byte = None

    tempo_limite = 120 # Tempo limite de 5 minutos em segundos
    start_time = time.time()  # Marca o tempo de início
    contador_de_ciclos = 0

    while True:  # Verifica se o tempo decorrido é menor que 5 minutos
        data = plc.db_read(db_number, byte_index, 1)
        byte = bytearray(data)
        # print('meu byte')
        # print(byte)

        if byte != old_byte:
            thSave = threading.Thread(target=save_data, args=(experiment_number, byte, sensors, contador, txt_filename, csv_filename))
            thSave.start()
            old_byte = byte.copy()
            start_time = time.time()
            contador = contador + 1
        
        contador_de_ciclos = contador_de_ciclos + 1

        tempo_final = time.time()

        if(start_time - tempo_final > tempo_limite):
            print(start_time - tempo_final)
            break

    print(time.time() - start_time)
    print(contador)

    last_experiment_id = banco.get_last_experiment_id()  # Pegando o último experimento realizado

    # Coletando uma lista de pulse_train do último experimento
    pulse_trains = banco.get_pulse_values_by_experiment(last_experiment_id)

    print('Trens de pulsos para serem cadastrados: \n')
    pulse_trains_str = "[" + ",".join(map(str, pulse_trains)) + "]"
    print(pulse_trains_str)

    #agora vou inserir no banco de dados o trem de pulso que vou enviar para o chat GPT
    try:

        banco.insert_pattern(experiment_number, pulse_trains_str)        
        print('Trem de pulso inserido no banco!')
        print('Experimento: ', experiment_number)
    except Exception as e:

        print(f"Erro ao inserir o trem de pulso no banco: {e}")

    exit(1)


if __name__ == '__main__':

    # plc_ip = "172.21.1.1"
    plc_ip = "192.168.0.10"
    rack = 0
    slot = 1


    while True:

        magFront = connect_to_plc(plc_ip, rack, slot)

        if magFront:
            print('PLC conectado!')

            byte_index = 0

            try:
                monitor_plc(magFront, db_number=24, byte_index=byte_index)
            except Exception as e:
                print(f'[IP: {plc_ip}] Erro ao tentar coletar dados do PLC. Ocorreu o seguinte erro: {e}\n\n')
                time.sleep(5)
            
            magFront.disconnect()
        else:
            print("Não foi possível conectar ao PLC\n\n")
            time.sleep(5)

