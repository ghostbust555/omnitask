import datetime
import os
import traceback
from threading import Thread
from time import sleep

from CommandRunner import CommandRunner
from FinishedJobStore import FinishedJobsStore
from GitHelper import gitClone


class JobRunner(Thread):
    def __init__(self, cloneBaseDir:str, pendingJobQueue:list, activeJobQueue:list, completedJobs:FinishedJobsStore):
        Thread.__init__(self)
        self.PendingJobQueue = pendingJobQueue
        self.ActiveJobQueue = activeJobQueue
        self.CloneBaseDir = cloneBaseDir
        self._stopped = True
        self.CompletedJobs = completedJobs
        self.JobCounter = completedJobs.loadSavedJobs()

    def stop(self):
        self._stopped = True

    def run(self):
        self._stopped = False

        if not os.path.exists(self.CloneBaseDir):
            os.mkdir(self.CloneBaseDir)

        while not self._stopped:
            if len(self.PendingJobQueue) > 0:
                job = self.PendingJobQueue.pop()
                try:
                    job.Status = "Active"
                    self.ActiveJobQueue.append(job)

                    print(job)

                    cloneDir = "{}/{}".format(self.CloneBaseDir, job.JobId)
                    os.mkdir(cloneDir)

                    start = datetime.datetime.now()
                    job.Start = str(start)

                    output, err, p = gitClone(cloneDir, job)

                    print(output)
                    print(err)

                    rc = p.returncode

                    if rc != 0:
                        job.Stop = str(datetime.datetime.now())
                        job.Status = "GitFailed"
                        job.ReturnCode = rc
                        job.StdErr = err
                        job.StdOut = output

                        self.CompletedJobs.add(job)
                        self.ActiveJobQueue.pop()
                    else:
                        requirementsPath = os.path.abspath(cloneDir+"/requirements.txt")
                        
                        if os.path.exists(requirementsPath):
                             p = CommandRunner.RunCommand(['pip', "install", "-r", requirementsPath], job)

                        p = CommandRunner.RunCommand(['python', '-m', job.Src.replace(".py", "").replace("/", ".").replace("\\", "."), job.Parameters], job, dir=cloneDir)

                        print("JOB OUT-"+job.StdOut)
                        print("JOB ERR-"+job.StdErr)

                        job.Stop = str(datetime.datetime.now())
                        job.ReturnCode = p.poll()

                        job.Status = "Complete" if job.ReturnCode == 0 else "Failed"
                        self.CompletedJobs.add(job)
                        self.ActiveJobQueue.pop()
                except Exception as e:
                    job.Finish = str(datetime.datetime.now())
                    job.StdErr = "Internal OmniTask Failure "+str(traceback.format_exc())
                    job.Status = "Failed"
                    job.Stop = str(datetime.datetime.now())
                    self.CompletedJobs.add(job)
                    self.ActiveJobQueue.pop()

            sleep(1)

