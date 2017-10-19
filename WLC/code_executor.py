import io
import logging
import sys
import docker

LOGGER = logging.getLogger()

DEFAULT_DOCKER_PORT = 2375


class CodeExecutor:
    def __init__(self, docker_ip=None):
        self.docker_ip = docker_ip
        self.docker_port = DEFAULT_DOCKER_PORT
        self.client = None

    def connect_sandbox(self, docker_ip):
        if docker_ip:
            # save the address
            self.docker_ip = docker_ip

            # attempt TCP connection
            self.client = docker.DockerClient(base_url="tcp://{}:{}".format(self.docker_ip, self.docker_port))
            LOGGER.info("Docker Version running on server: %s\n", self.client.version()["Version"])

    def execute_code(self, code):
        LOGGER.info("Executing code: \n%s\n", code)

        if not self.docker_ip:
            self.execute_local(code)
        else:
            self.execute_sandbox(code)

    def execute_local(self, code):
        with io.StringIO() as code_out:
            sys.stdout = code_out

            try:
                exec(code)
            except:
                LOGGER.exception("An error was raised!")
            else:
                LOGGER.info("No errors occurred.")

            sys.stdout = sys.__stdout__

            s = code_out.getvalue()

            LOGGER.info("Output:\n%s\n", s)

    def execute_sandbox(self, code):
        client = docker.DockerClient(base_url="tcp://{}:2375".format(self.docker_ip))
        LOGGER.info("\n\n  # Docker Version running on server: %s\n", client.version()["Version"])

        container = client.containers.run('python', 'python -c \"{}\"'.format(code), detach=True)
        container.wait()

        LOGGER.info("\n\n # Container stdout contents: \n%s\n", container.logs(stdout=True))

        LOGGER.info("\n\n # Container stderr contents: \n%s\n", container.logs(stderr=True))
