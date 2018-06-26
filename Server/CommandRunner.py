import queue
import subprocess
import threading
import time

from Job import Job


class AsynchronousFileReader(threading.Thread):
    '''
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''

    def __init__(self, fd, q:queue.Queue, p:subprocess):
        assert isinstance(q, queue.Queue)
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self._fd = fd
        self._queue = q
        self._proc =p

    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            if line is not None and line != b'':
                self._queue.put(line)
            elif self._proc.poll() is None:
                raise SystemExit()

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self._queue.empty()

class CommandRunner:
    @staticmethod
    def RunCommand(command, job:Job, verbose = False, dir=None):
        '''
        Example of how to consume standard output and standard error of
        a subprocess asynchronously without risk on deadlocking.
        '''

        print(command)
		
        # Launch the command as subprocess.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=dir)

        job._process = process

        # Launch the asynchronous readers of the process' stdout and stderr.
        stdout_queue = queue.Queue()
        stdout_reader = AsynchronousFileReader(process.stdout, stdout_queue, process)
        stdout_reader.start()
        stderr_queue = queue.Queue()
        stderr_reader = AsynchronousFileReader(process.stderr, stderr_queue, process)
        stderr_reader.start()

        # Check the queues if we received some output (until there is nothing more to get).
        while (not stdout_reader.eof() or not stderr_reader.eof()) and process.poll() is None:
            # Show what we received from standard output.
            while stdout_reader.isAlive() and not stdout_queue.empty() or stdout_queue:
                try:
                    line = stdout_queue.get_nowait()
                    job.StdOut += line.decode()+"\n"

                    if verbose:
                        print(line.decode())
                except queue.Empty:
                    break

            # Show what we received from standard error.
            while stderr_reader.isAlive() and not stderr_queue.empty():
                try:
                    line = stderr_queue.get_nowait()
                    job.StdErr += line.decode()+"\n"

                    if verbose:
                        print(line.decode())
                except queue.Empty:
                    break

            # Sleep a bit before asking the readers again.
            time.sleep(.1)

        # Let's be tidy and join the threads we've started.
        stdout_reader.join()
        stderr_reader.join()

        # Close subprocess' file descriptors.
        process.stdout.close()
        process.stderr.close()

        return process