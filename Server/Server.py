import datetime
import json
import os
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep

import cherrypy
import psutil

jobsQueue = []
jobCounter = 0

class Job:
    def __init__(self, gitRepo:str, gitBranch:str, src:str, parameters:str, jobId:int):
        self.GitRepo = gitRepo
        self.GitBranch = gitBranch
        self.Src = src
        self.Parameters = parameters
        self.JobId = jobId

class JobResult:
    def __init__(self, stdOut:str, stdErr:str, processCodeResult:int, start:str, stop:str, resultObject:str):
        self.StdOut = stdOut
        self.StdErr = stdErr
        self.ProcessCodeResult = processCodeResult
        self.Start = start
        self.Stop = stop
        self.ResultObject = resultObject

class FinishedJobsStore:
    def __init__(self, folderPath:str):
        global jobCounter

        self.FolderPath = folderPath
        self._finishedJobs = {}

        for name in os.listdir(self.FolderPath):
            try:
                jobCounter = max(jobCounter, int(name)+1)

                with open(self.FolderPath+"/"+name+"/output.json") as f:
                    data = json.load(f)
                    self._finishedJobs[data["Job"]["JobId"]] = data

            except ValueError:
                pass

    def add(self, job:Job, jobResult:JobResult):
        self._finishedJobs[job.JobId] = {
                "Job":job.__dict__,
                "JobResult":jobResult.__dict__
            }

        thisJobOutputDir = "{}/{}".format(self.FolderPath, job.JobId)

        os.mkdir(thisJobOutputDir)

        with open(thisJobOutputDir+"/output.json", "w") as jobFile:
            jobFile.write(json.dumps({
                "Job":job.__dict__,
                "JobResult":jobResult.__dict__
            }))
            jobFile.close()

    def get(self):
        return self._finishedJobs


class JobRunner(Thread):
    def __init__(self, cloneBaseDir:str, jobQueue:list, completedJobs:FinishedJobsStore):
        Thread.__init__(self)
        self.JobQueue = jobQueue
        self.CloneBaseDir = cloneBaseDir
        self._stopped = True
        self.CompletedJobs = completedJobs

    def stop(self):
        self._stopped = True

    def run(self):
        self._stopped = False

        while not self._stopped:
            if len(self.JobQueue) > 0:
                job = self.JobQueue.pop()
                print(job)

                cloneDir = "{}/{}".format(self.CloneBaseDir, job.JobId)
                os.mkdir(cloneDir)

                start = datetime.datetime.now()

                p = Popen(['git', 'clone', '-b', job.GitBranch, job.GitRepo, cloneDir], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                output, err = p.communicate()
                print(output)
                print(err)
                rc = p.returncode

                if rc != 0:
                    jr = JobResult(output.decode(), err.decode(), rc, str(start), str(datetime.datetime.now()), "Git Clone Failed.")

                    self.CompletedJobs.add(job, jr)
                else:
                    p = Popen(['python', "{}/{}".format(cloneDir, job.Src), job.Parameters], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                    output, err = p.communicate()
                    print(output)
                    print(err)
                    rc = p.returncode

                    jr = JobResult(output.decode(), err.decode(), rc, str(start), str(datetime.datetime.now()), "")

                    self.CompletedJobs.add(job, jr)
            sleep(1)

class JobsController(object):
    def __init__(self, jobQueue:list, finishedJobs:FinishedJobsStore):
        self.JobQueue = jobQueue
        self.FinishedJobs = finishedJobs

    @cherrypy.expose
    def getMachineState(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        return json.dumps(
            {
                "CPU" : psutil.cpu_percent(),
                "Memory" : psutil.virtual_memory().free >> 20
            }).encode()

    @cherrypy.expose
    def addJob(self, gitRepo:str, gitBranch:str, src:str, parameters:str):
        global jobCounter

        self.JobQueue.insert(0, Job(gitRepo, gitBranch, src, parameters, jobCounter))
        jobCounter += 1

        return "ok"

    @cherrypy.expose
    def getJobs(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        def mergeDicts(a,b):
            merged = dict()
            merged.update(a)
            merged.update(b)

            return merged

        allJobs = self.JobQueue + [mergeDicts(row['Job'], row['JobResult']) for row in list(self.FinishedJobs.get().values())]

        def obj_dict(obj):
            return obj.__dict__

        return json.dumps(allJobs, default=obj_dict).encode()

    @cherrypy.expose
    def test(self, num):
        return num



completedJobs = FinishedJobsStore("C:/test/logs")

jr = JobRunner("C:/test/repos", jobsQueue, completedJobs)
jr.start()

jobsQueue.insert(0, Job("https://github.com/leachim6/hello-world.git", 'master', 'p/python3.py', '', jobCounter))
jobCounter += 1

static_dir = os.path.dirname(os.path.abspath(__file__))+"/src"
print("\nstatic_dir: %s\n" % static_dir)

conf = {
        '/': {  # Root folder.
            'tools.staticdir.on':   True,  # Enable or disable this rule.
            'tools.staticdir.root': static_dir,
            'tools.staticdir.dir':  '',
            'tools.staticdir.index' : "index.html"
        }
    }

cherrypy.quickstart(JobsController(jobsQueue, completedJobs), '/', config=conf)