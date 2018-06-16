class Job:
    def __init__(self, gitRepo:str, gitBranch:str, src:str, parameters:str, jobId:int):
        self.GitRepo = gitRepo
        self.GitBranch = gitBranch
        self.Src = src
        self.Parameters = parameters
        self.JobId = jobId
        self.Status = "Pending"
        self.StdOut = ""
        self.StdErr = ""
        self.ReturnCode = None
        self.Start = None
        self.Stop = None
        self.ResultObject = None
        self._process = None

    def getAsDictOfOnlyLogs(self):
        return {
            "StdOut" : self.StdOut,
            "StdErr" : self.StdErr,
            "JobId" : self.JobId,
        }

    def getAsDictWithoutLogs(self):
        return {
            "GitRepo" : self.GitRepo,
            "GitBranch" : self.GitBranch,
            "Src" : self.Src,
            "Parameters" : self.Parameters,
            "JobId" : self.JobId,
            "Status" : self.Status,
            "ReturnCode" : self.ReturnCode,
            "Start" : self.Start,
            "Stop" : self.Stop,
            "ResultObject" : self.ResultObject
        }