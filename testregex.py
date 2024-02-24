import threading
import time


start_time = [0, 0, 0]
task0 = 5
task1 = 10
task2 = 20
def background_task():
    while True:
        # Catat waktu awal eksekusi
        for Stime in range(len(start_time)):
            
            if start_time[Stime] == 0:
                start_time[Stime] = time.time()
        
        if time.time() - start_time[0] > task0:
            print('task0')
            start_time[0] = time.time()

        if time.time() - start_time[1] > task1:
            print('task1')
            start_time[1] = time.time()
        
        if time.time() - start_time[2] > task2:
            print('task2')
            start_time[2] = time.time()


background_thread = threading.Thread(target=background_task)
# Set daemon agar thread berhenti ketika program utama berhenti
# background_thread.daemon = True

background_thread.start()
# background_task()