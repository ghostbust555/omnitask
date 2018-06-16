from subprocess import Popen, PIPE

def gitClone(cloneDir, job):
    p = Popen(['git', 'clone', '-b', job.GitBranch, job.GitRepo, cloneDir], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    return output.decode(), err.decode(), p

def gitListBranches(gitRepo:str):
    p = Popen(['git', 'ls-remote', '-h', gitRepo], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    return output.decode(), err.decode(), p