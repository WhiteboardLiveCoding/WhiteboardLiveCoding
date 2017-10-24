import io
import logging
import sys
import docker

LOGGER = logging.getLogger()

DEFAULT_DOCKER_PORT = "2375"


class CodeExecutor:
    def __init__(self, ip="", port=""):
        if ip and port:
            self.client = docker.DockerClient(base_url="tcp://{}:{}".format(ip, port))
            self.force_local = False
        else:
            self.force_local = True

    def execute_code(self, code):
        LOGGER.info("Executing code: \n%s\n", code)

        if self.force_local:
            return self.execute_local(code)
        else:
            self.execute_sandbox(code)

    def execute_local(self, code):
        with io.StringIO() as code_out:
            sys.stdout = code_out

            try:
                exec(code)
            except Exception as e:
                LOGGER.exception("An error was raised!")
                return str(e)
            else:
                LOGGER.info("No errors occurred.")

            sys.stdout = sys.__stdout__

            s = code_out.getvalue()

            LOGGER.info("Output:\n%s\n", s)

    def execute_sandbox(self, code):
        LOGGER.info("Executing in sandbox...\n")
        container = self.client.containers.run('python', 'python -c \"{}\"'.format(code), detach=True)
        container.wait()

        LOGGER.info("\n\n # Container output: \n%s\n", container.logs(stdout=True))
