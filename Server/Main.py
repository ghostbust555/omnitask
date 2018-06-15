import json
import os

import cherrypy
import psutil

from Server.FinishedJobStore import FinishedJobsStore
from Server.Job import Job
from Server.JobRunner import JobRunner

pendingJobsQueue = []
activeJobsQueue = []
completedJobs = FinishedJobsStore("C:/test/logs")

def obj_dict(obj):
    return dict([(key,value) for key, value in obj.__dict__.items() if key not in ["StdOut", "StdErr"]])

def output_dict(obj):
    return dict([(key,value) for key, value in obj.__dict__.items() if key in ["StdOut", "StdErr"]])

def removeOutput(obj):
    return [dict([(key,value) for key, value in y.items() if key not in ["StdOut", "StdErr"]]) for y in obj]

def onlyOutput(obj):
    return [dict([(key,value) for key, value in y.items() if key in ["StdOut", "StdErr"]]) for y in obj]

def getAllJobs():
    return [x.__dict__ for x in pendingJobsQueue] + [x.__dict__ for x in activeJobsQueue] + [row['Job'] for row in list(completedJobs.get().values())]

class JobsController(object):
    def __init__(self, pendingJobQueue:list, activeJobQueue:list, finishedJobs:FinishedJobsStore):
        self.PendingJobQueue = pendingJobQueue
        self.ActiveJobQueue = activeJobQueue
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
        self.PendingJobQueue.insert(0, Job(gitRepo, gitBranch, src, parameters, jr.JobCounter))
        jr.JobCounter += 1

        return "ok"

    @cherrypy.expose
    def getJobOutput(self, jobId):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        allJobs = getAllJobs()

        selectedJob = next(x for x in allJobs if x["JobId"] == int(jobId))

        return json.dumps({"StdOut":selectedJob["StdOut"], "StdErr":selectedJob["StdErr"]}, default=output_dict).encode()

    @cherrypy.expose
    def getJobs(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        def mergeDicts(a,b):
            merged = dict()
            merged.update(a)
            merged.update(b)

            return merged

        allJobs = removeOutput(getAllJobs())

        return json.dumps(allJobs, default=obj_dict).encode()

    @cherrypy.expose
    def test(self, num):
        return num


jr = JobRunner("C:/test/repos", pendingJobsQueue, activeJobsQueue, completedJobs)
jr.start()

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

cherrypy.quickstart(JobsController(pendingJobsQueue, activeJobsQueue, completedJobs), '/', config=conf)