import json
import os
import socket
import threading
import traceback

import cherrypy
import psutil

from Server import CommandRunner
from Server.FinishedJobStore import FinishedJobsStore
from Server.GitHelper import gitListBranches
from Server.Job import Job
from Server.JobRunner import JobRunner

jobsRootPath = os.path.expanduser('~')+"/OmniTasks"

print("Hosting OmniTasks, clone location {}".format(jobsRootPath))

if not os.path.exists(jobsRootPath):
    os.mkdir(jobsRootPath)

pendingJobsQueue = []
activeJobsQueue = []
completedJobs = FinishedJobsStore(jobsRootPath+"/logs")

def output_dict(obj):
    return obj.__dict__

def removeOutput(obj):
    return dict([(key,value) for key, value in obj.items() if key not in ["StdOut", "StdErr"]])

def onlyOutput(obj):
    return dict([(key,value) for key, value in obj.items() if key in ["StdOut", "StdErr", "JobId"]])

def getAllJobsWithoutLogs():
    return [x.getAsDictWithoutLogs() for x in pendingJobsQueue] + [x.getAsDictWithoutLogs() for x in activeJobsQueue] + [removeOutput(row['Job']) for row in list(completedJobs.get().values())]

def getAllJobsWithOnlyLogs():
    return [x.getAsDictOfOnlyLogs() for x in pendingJobsQueue] + [x.getAsDictOfOnlyLogs() for x in activeJobsQueue] + [onlyOutput(row['Job']) for row in list(completedJobs.get().values())]

class JobsController(object):
    def __init__(self, pendingJobQueue:list, activeJobQueue:list, finishedJobs:FinishedJobsStore):
        self.PendingJobQueue = pendingJobQueue
        self.ActiveJobQueue = activeJobQueue
        self.FinishedJobs = finishedJobs

    @cherrypy.expose
    def stopJob(self, jobId:str):
        try:
            selectedJobs = [job for job in self.ActiveJobQueue if str(job.JobId) == jobId]
            pendingSelectedJobs = [job for job in self.PendingJobQueue if str(job.JobId) == jobId]

            if len(selectedJobs) > 0:
                selectedJob = selectedJobs[0]

                if selectedJob._process is not None and selectedJob._process.poll() is None:
                    selectedJob._process.kill()
            elif len(pendingSelectedJobs) > 0:
                self.PendingJobQueue.remove(selectedJobs[0])
            else:
                raise cherrypy.HTTPError(500, "Job not found in any queue!")

            return "ok"
        except Exception:
            raise cherrypy.HTTPError(500, str(traceback.format_exc()))


    @cherrypy.expose
    def getGitBranches(self, gitRepo:str):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        output, err, p = gitListBranches(gitRepo)

        if p.returncode != 0:
            raise cherrypy.HTTPError(500, err+"\n"+output)

        return json.dumps(
            {
                "Branches" : [x.split("\t")[1].split("refs/heads/")[1] for x in output.strip().split("\n")]
            }).encode()

    @cherrypy.expose
    def getMachineState(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        return json.dumps(
            {
                "CPU" : psutil.cpu_percent(),
                "Memory" : psutil.virtual_memory().free >> 20
            }).encode()

    @cherrypy.expose
    def addJob(self, gitRepo:str, gitBranch:str, src:str, parameters:str, tag:str):
        self.PendingJobQueue.insert(0, Job(gitRepo, gitBranch, src, parameters, jr.JobCounter, tag))
        jr.JobCounter += 1

        return "ok"

    @cherrypy.expose
    def getJobOutput(self, jobId):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        allJobs = getAllJobsWithOnlyLogs()

        selectedJob = next(x for x in allJobs if str(x["JobId"]) == jobId)

        return json.dumps(selectedJob, default=output_dict).encode()

    @cherrypy.expose
    def getJobs(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        def mergeDicts(a,b):
            merged = dict()
            merged.update(a)
            merged.update(b)

            return merged

        allJobs = getAllJobsWithoutLogs()

        return json.dumps(allJobs).encode()

    @cherrypy.expose
    def test(self, num):
        return num


jr = JobRunner(jobsRootPath+"/repos", pendingJobsQueue, activeJobsQueue, completedJobs)
jr.start()

static_dir = os.path.dirname(os.path.abspath(__file__))+"/src"
print("\nstatic_dir: %s\n" % static_dir)

conf = {
    '/': {  # Root folder.
        'tools.staticdir.on':   True,  # Enable or disable this rule.
        'tools.staticdir.root': static_dir,
        'tools.staticdir.dir':  '',
        'tools.staticdir.index' : "index.html",
    }
}

def launchTensorBoard(tensorBoardPath):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((socket.gethostname(),6006))

    if result == 0:
       print("Tensorboard is open at http://"+socket.gethostname()+":6006")
    else:
       CommandRunner.CommandRunner.RunCommand('tensorboard --logdir=' + tensorBoardPath, Job("","","","",-1), True)


t = threading.Thread(target=launchTensorBoard, args=([jobsRootPath]), daemon=True)
t.start()

#cherrypy.server.socket_host = socket.gethostname().lower()
cherrypy.quickstart(JobsController(pendingJobsQueue, activeJobsQueue, completedJobs), '/', config=conf)