import json
import os

from Server.Job import Job


class FinishedJobsStore:
    def __init__(self, folderPath:str):
        self.FolderPath = folderPath
        self._finishedJobs = {}

    def loadSavedJobs(self):
        jobCounter = 0

        for name in os.listdir(self.FolderPath):
            try:
                jobCounter = max(jobCounter, int(name)+1)

                with open(self.FolderPath+"/"+name+"/output.json") as f:
                    data = json.load(f)
                    self._finishedJobs[data["Job"]["JobId"]] = data

            except ValueError:
                pass

        return jobCounter


    def add(self, job:Job):
        self._finishedJobs[job.JobId] = {
                "Job":job.__dict__
            }

        thisJobOutputDir = "{}/{}".format(self.FolderPath, job.JobId)

        os.mkdir(thisJobOutputDir)

        with open(thisJobOutputDir+"/output.json", "w") as jobFile:
            jobFile.write(json.dumps({
                "Job":job.__dict__
            }))
            jobFile.close()

    def get(self):
        return self._finishedJobs