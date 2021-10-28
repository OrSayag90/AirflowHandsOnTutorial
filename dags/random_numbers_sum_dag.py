import json
import os
import random
from datetime import timedelta, datetime
from textwrap import dedent
from time import time, clock

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator
from airflow.sensors.python import PythonSensor

NUM_OF_RANDOM_NUMBERS_TO_GENERATE = 10
MAX_INTEGER = 100
GENERATED_NUMBERS_KEYWORD = "generated_numbers"


def generate_path_to_file():
    try:
        output_path = Variable.setdefault("LOCAL_PATH", '/tmp/')
    except Exception:
        output_path = '/tmp/'
    timestamp = str(int(time()))
    filename = '{}.json'.format(timestamp)
    return os.path.join(output_path, filename)


def generate():
    generated_random_numbers = [random.randint(1, MAX_INTEGER) for entry in
                                range(0, NUM_OF_RANDOM_NUMBERS_TO_GENERATE)]
    numbers_dict = {GENERATED_NUMBERS_KEYWORD: generated_random_numbers}
    print("generated the numbers:" + str(generated_random_numbers))
    path_to_file = generate_path_to_file()

    with open(path_to_file, 'w') as json_file:
        print("writing numbers list to path:" + path_to_file)
        json.dump(numbers_dict, json_file)
    return path_to_file


def check_file_exists(**kwargs):
    ti = kwargs['ti']
    numbers_file_path = ti.xcom_pull(task_ids='generate_task_id')
    return os.path.isfile(numbers_file_path)


def transform(**kwargs):
    ti = kwargs['ti']
    numbers_file_path = ti.xcom_pull(task_ids='generate_task_id')
    with open(numbers_file_path, 'r') as json_file:
        print("reading numbers list from path:" + numbers_file_path)
        numbers = json.load(json_file)[GENERATED_NUMBERS_KEYWORD]
        print("numbers list:" + str(numbers))
        total_order_value = 0
        for value in numbers:
            total_order_value += value
        total_value = {"sum": total_order_value}
        total_value_json_string = json.dumps(total_value)
        ti.xcom_push('total_order_value', total_value_json_string)
    os.remove(numbers_file_path)


def load(**kwargs):
    ti = kwargs['ti']
    total_value_string = ti.xcom_pull(task_ids='transform_task_id', key='total_order_value')
    total_order_value = json.loads(total_value_string)['sum']
    print("Sum is: " + str(total_order_value))


# Default settings applied to all tasks
default_args = {
    'owner': 'king_arthur',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'start_date': datetime(2021, 1, 1),
}

# Using a DAG context manager, you don't have to specify the dag property of each task
with DAG(dag_id='generate_number_and_sum_dag',
         schedule_interval='*/5 * * * *',  # run every 5 minutes
         default_args=default_args,
         catchup=False  # enable if you don't want historical dag runs to run
         ) as dag:
    random.seed(clock())

    # Instantiate tasks
    transform_task = PythonOperator(
        task_id='transform_task_id',
        python_callable=transform
    )

    check_file_exists_sensor = PythonSensor(
        task_id="check_file_exists_task_sensor",
        python_callable=check_file_exists,
        poke_interval=30    # retries check if file exists every 30 seconds
    )

    generate_task = PythonOperator(
        task_id='generate_task_id',
        python_callable=generate
    )

    load_task = PythonOperator(
        task_id='load_task_id',
        python_callable=load
    )

    generate_task.doc_md = dedent(
        """\
    #### Generate task
    A simple Generate task to generate a list of 10 random numbers and write it to a json file for the rest of the data pipeline.
    This file path is then put into xcom, so that it can be processed by the next task.
    """
    )

    check_file_exists_sensor.doc_md = dedent(
        """\
    #### Check file exists sensor
    A simple sensor task which checks if the JSON file generated in Generate task was created
    """
    )

    transform_task.doc_md = dedent(
        """\
    #### Transform task
    A simple Transform task which takes in the path of the file with the collection of the random numbers from xcom
    and computes the total order value.
    This computed value is then put into xcom, so that it can be processed by the next task.
    """
    )

    load_task.doc_md = dedent(
        """\
    #### Load task
    A simple Load task which takes in the result of the Transform task, by reading it
    from xcom and instead of saving it to end user review, just prints it out.
    """
    )

    generate_task >> check_file_exists_sensor >> transform_task >> load_task
