# AirflowHandsOnTutorial
This repository introduces Apache Airflow by walking through some fundamental Airflow concepts and their usage while writing a first pipeline.

## Documentation
The Airflow overview is available in the repo's [wiki](https://github.com/OrSayag90/AirflowHandsOnTutorial/wiki)

## Airflow Installation 
### Prerequisites
1. Install Docker Community Edition (CE) on your workstation.
1. Configure your Docker instance to use 4.00 GB of memory for all containers to run properly.
1. Install Docker Compose v1.29.1 or newer on your workstation.
1. Install curl for downloading the docker-compose.yaml file.

### Install Airflow on docker compose
Run the script:  
```
 sh airflow_install.sh
 ```    
    
This script does the following:

a. Downloads the docker-compose.yaml file, which contains several service definitions:  
**airflow-scheduler** - The scheduler monitors all tasks and DAGs, then triggers the task instances once their dependencies are complete.  
**airflow-webserver** - The webserver is available at http://localhost:8080.  
**airflow-worker** - The worker that executes the tasks given by the scheduler.  
**airflow-init** - The initialization service.  
**flower** - The flower app for monitoring the environment. It is available at http://localhost:5555.  
**postgres** - The database.  
**redis** - The redis - broker that forwards messages from scheduler to worker.  

b. Initializes the databases by running database migrations and create the first user account.  
The account created has the login **airflow** and the password **airflow**.

c. Creates the airflow container mounted directories, which means that their contents are synchronized between your computer and the container:
    **./logs** - contains logs from task execution and scheduler.  
    **./plugins** - you can put your custom plugins here.    
    
  The following directories are also used by the container and already exists in the repository:  
  **./dags** - you can put your DAG files here. 
 
    
### Start all services:  
    ```
    docker-compose up -d
    ```

### Destroy Airflow
Stop airflow:  
        ```
        docker-compose down
        ```    
        
### Cleanup Airflow    
Clean up (stop and delete containers, delete volumes with database data and download images, logs and plugins):  
        ```
        sh airflow_destroy.sh
  
##  Creating a first DAG   
The simple DAG in this tutorial demonstrates the principles discussed in wiki and includes the following tasks:
1. Generate list of 10 random number, write to a JSON file and push the path to the file to a XCom.
2. Check JSON file exists with a sensor.
3. Load the numbers from the file, sum them and push it to a XCom.
4. Pull the sum and Json file path from the XComs, print the sum and delete the file.
This DAG will run every 5 minutes and start when we start all the _airflow_ services as we defined above.

### Steps to write an Airflow DAG
There are only 5 steps you need to remember to write an Airflow DAG or workflow:

Step 1: Importing modules
Step 2: Default Arguments
Step 3: Instantiate a DAG
Step 4: Tasks
Step 5: Setting up Dependencies

#### Step 1: Importing modules
Import Python dependencies needed for the workflow

        import json
        import os
        import random
        from datetime import timedelta, datetime
        from textwrap import dedent
        from time import time, clock
        from airflow import DAG
        from airflow.models import Variable
        from airflow.operators.python_operator import PythonOperator

#### Step 2: Default Arguments
Configure settings that are shared by all our tasks. 
Settings for tasks can be passed as arguments when creating them, 
but we can also pass a dictionary with default values to the DAG. This allows us to share default arguments for all the tasks in our DAG is the best place to set 
e.g. the owner and start date of our DAG.
    
    default_args = {
        'owner': 'king_arthur',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'start_date': datetime(2021, 1, 1),
    }


These settings tell Airflow that this workflow is owned by 'king_arthur', that the workflow is valid since January 1st of 2021,
it should not send emails and it is allowed to retry the workflow once if it fails with a delay of 5 minutes. 
Other common default arguments are email settings on failure and end time.

#### Step 3: Instantiate a DAG
We'll now create our DAG object. We name it _generate_number_and_sum_dag_and pass it some default args:
        
        with DAG(dag_id= 'generate_number_and_sum_dag',
                schedule_interval='*/5 * * * *',
                default_args=default_args,
                catchup=False
         ) as dag:

In schedule_interval='*/5 * * * *' we've specified a run at every 5 minutes (see www.crontab.guru to determine cron schedule expressions).

Airflow will generate DAG runs from the start_date with the specified _schedule_interval_. Once a DAG is active, 
Airflow continuously checks in the database if all the DAG runs have successfully run since the start_date. 
Any missing DAG runs are automatically scheduled. In example, when you initialize on 2021-04-01 a DAG with a start_date 
at 2021-01-01 and a daily schedule_interval, Airflow will schedule DAG runs for all the days between 2021-01-01 and 2021-04-01.
In this tutorial we're not interested in that behavior, and therefore set _catchup=False_

The rest of the settings are specified in the default_args we have set in the previous step.

#### Step 4: Tasks
The next step is to lay out all the tasks in the workflow.
As mentioned in wiki, tasks are represented by operators that either perform an action, transfer data, or sense if something has been done.
Examples of actions are running a bash script or calling a Python function.
We'll create a workflow consisting of three above tasks. All of them The first two are implemented with the PythonOperator. 
Every operator gets a unique task ID and function to run.

    generate_task = PythonOperator(
        task_id='generate_task_id',
        python_callable=generate
    )

    transform_task = PythonOperator(
        task_id='transform_task_id',
        python_callable=transform
    )

    load_task = PythonOperator(
        task_id='load_task_id',
        python_callable=load
    )

    check_file_exists_task = PythonSensor(
        task_id="check_file_exists_task_id",
        python_callable=check_file_exists,
        poke_interval=30    # retries check if file exists every 30 seconds
    )

**Task 1: Generate list of 10 random number, write to a JSON file and push the file path to a XCom**     
The _generate_ function is the callable that the task _generate_task_ runs.      
It uses the _random_ Python library to generate 10 numbers in range 0 to 100, dumps it to a json file in a predefined Python dictionary format and returns the file path.    
In the line `output_path = Variable.setdefault("LOCAL_PATH", '/tmp/')` we try to read an Airflow variable called _LOCAL_PATH_ and use it as the path to the JSON file.
The `Variable.setdefault` tries to read the variable value and if it doesn't exist sets it to `/tmp/`.
After the first execution this variable will be set and available for future executions. 
For the JSON file name, the method uses the timestamp to prevent duplications.    
In the last line of _generate_,it returns _path_to_file_, in this way it pushes a XCom with the task_id _generate_task_id_ as key and the path_to_file as a value.
This value is ready to read by the other tasks, just by specifying the XCom key.
 
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


    def generate_path_to_file():
        try:
            output_path = Variable.setdefault("≈", '/tmp/')
        except Exception:
            output_path = '/tmp/'
        timestamp = str(int(time()))
        filename = '{}.json'.format(timestamp)
        return os.path.join(output_path, filename)

**Task 2: Check JSON file exists with a sensor**      
The _check_file_exists_ function is the callable that the sensor _check_file_exists_sensor_ runs.      
In the line `numbers_file_path = ti.xcom_pull(task_ids='generate_task_id')` it pulls the JSON file path from the XCom defined in _generate_task_. 
It uses the _os_ Python library to check if the file exists.     
This sensor has a _poke_interval_ of 30 seconds which means as long as the file doesn't exist it will retry every 30 seconds.

    def check_file_exists(**kwargs):
        ti = kwargs['ti']
        numbers_file_path = ti.xcom_pull(task_ids='generate_task_id')
        return os.path.isfile(numbers_file_path)


**Task 3: Read the numbers list from the file and push their sum to a XCom**      
The _transform_ function is the callable that the task _transform_task_ runs.      
In the line `numbers_file_path = ti.xcom_pull(task_ids='generate_task_id')` it pulls the JSON file path from the XCom defined in _generate_task_. 
It uses the _json_ Python library to read and parse the random numbers generated in the previous task, sums them and decode it.
Then it explicitly pushes the decoded sum to a XCom and names it `total_order_value`.
In the last line it removes the JSON file.

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
        
        
**Task 4: Pull the numbers sum and print it**     
The _load_ function is the callable that the task _load_task_ runs.     
In the line `total_value_string = ti.xcom_pull(task_ids='transform_task_id', key='total_order_value')` it pulls the decoded random numbers sum from the XCom. 
Then it parses and prints it.

    def load(**kwargs):
        ti = kwargs['ti']
        total_value_string = ti.xcom_pull(task_ids='transform_task_id', key='total_order_value')
        total_order_value = json.loads(total_value_string)['sum']
        print("Sum is: " + str(total_order_value))   
        
#### Step 5: Setting up Dependencies  
Set the order in which the tasks should be executed.
Since the order should be generate, check, transform and load- the dependencies should be defined as follows:
    
    generate_task >> check_file_exists_sensor >> transform_task >> load_task
    
### Recap    
A DAG is just a Python file, which is used to organize tasks and set their execution context. DAGs do not perform any actual computation.
Instead, tasks are the element of Airflow that actually “do the work” we want to be performed. 
It is your job to write the configuration and organize the tasks in specific orders to create a complete data pipeline.  
The full code of the _generate_number_and_sum_dag_ DAG we defined above can is located [here](dags/random_numbers_sum_dag.py)