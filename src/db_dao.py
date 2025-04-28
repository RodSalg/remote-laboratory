import mysql.connector
from mysql.connector import Error

class RemoteLaboratoryDAO:
    
    def __init__(self) -> None:
        pass

    def get_banco(self):

        try:

            mydb = mysql.connector.connect(
                host='localhost',
                database='cae_dr',
                user='root',
                password='1234')

            return mydb

        except mysql.connector.Error as e:

            print("Erro ao acessar o banco de dados:", e)

    def get_verificacao_foto(self) -> int:
        
        try:

            mydb = self.get_banco()
            cursor = mydb.cursor()

            comando = 'SELECT State FROM cae_dr.variablesofsystem WHERE `Function` = "cameraControl"'

            cursor.execute(comando)
            result = cursor.fetchone()

            return result[0] if result else None
        
        except mysql.connector.Error as e:

            print("Erro ao acessar a tabela: \n", e)



    def insert_data_into_database(self,experiment_number, step, pulse_train, pulse_value, time_to_change, experiment_name):
        
        sql = f'INSERT INTO `cae_dr`.`dadoscoletados2` ( `experiment_id`,`step`, `pulse_train`, `pulse_value`, `experimentName`, `timeToChange`) VALUES ({experiment_number}, {step}, "{pulse_train}", {pulse_value}, "{experiment_name}", "{time_to_change}");'
        
        try:

            mydb = self.get_banco()

            mycursor = mydb.cursor()

            mycursor.execute(sql)

            mydb.commit()      

        except Error as e:
            
            print(f"Erro ao tentar inserir os dados no banco de dados: \n {e}")

        finally:
            
            mydb.close()


    def get_last_experiment_id(self):
        try:
            mydb = self.get_banco()
            cursor = mydb.cursor()

            sql = "SELECT MAX(experiment_id) FROM dadoscoletados2"
            cursor.execute(sql)

            result = cursor.fetchone()

            return result[0] if result[0] is not None else None

        except mysql.connector.Error as e:
            print("Erro ao acessar a tabela:", e)
            return None

        finally:
            
            if mydb.is_connected():
                cursor.close()
                mydb.close()

    def get_pulse_values_by_experiment(self, experiment_id):

        try:
            mydb = self.get_banco()
            cursor = mydb.cursor()

            sql = "SELECT pulse_value FROM dadoscoletados2 WHERE experiment_id = %s ORDER BY step ASC"
            cursor.execute(sql, (experiment_id,))

            results = cursor.fetchall()

            pulse_values = [row[0] for row in results]

            return pulse_values

        except mysql.connector.Error as e:
            print("Erro ao acessar a tabela:", e)
            return []

        finally:
            if mydb.is_connected():
                cursor.close()
                mydb.close()


    def insert_pattern(self, experiment_id, pattern):
        try:
            mydb = self.get_banco()
            cursor = mydb.cursor()

            sql = """
            INSERT INTO dadoscoletados_summary (experiment_id, pattern)
            VALUES (%s, %s);
            """

            cursor.execute(sql, (experiment_id, pattern))

            mydb.commit()

        except mysql.connector.Error as e:
            print("Erro ao inserir o padrão na tabela:", e)

        finally:
            if mydb.is_connected():
                cursor.close()
                mydb.close()

    def get_patterns_by_experiment(self, experiment_id):

        try:
            mydb = self.get_banco()
            cursor = mydb.cursor()

            sql = "SELECT pattern FROM dadoscoletados_summary WHERE experiment_id = %s ORDER BY id DESC"
            cursor.execute(sql, (experiment_id,))

            results = cursor.fetchall()

            patterns = [row[0] for row in results]

            return patterns[0]

        except mysql.connector.Error as e:
            print("Erro ao acessar a tabela:", e)
            return []

        finally:

            if mydb.is_connected():
                
                cursor.close()
                mydb.close()


# teste = RemoteLaboratoryDAO()


