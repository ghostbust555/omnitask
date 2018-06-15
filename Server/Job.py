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