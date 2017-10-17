import io
import logging
import sys
import docker

LOGGER = logging.getLogger()


class CodeExecutor:
    def __init__(self):
        pass

    def execute_code(self, code, docker_ip):
        LOGGER.info("Executing code: \n%s\n", code)

        with io.StringIO() as code_out:
            sys.stdout = code_out

            self.execute_code_docker(code, docker_ip)

            # try:
            #     exec(code)
            # except:
            #     LOGGER.exception("An error was raised!")
            # else:
            #     LOGGER.info("No errors occurred.")
            #
            # sys.stdout = sys.__stdout__
            #
            # s = code_out.getvalue()
            #
            # LOGGER.info("Output:\n%s\n", s)

    def execute_code_docker(self, code, docker_ip):
        client = docker.DockerClient(base_url="tcp://{}:2375".format(docker_ip))
        LOGGER.info("\n\n  # Docker Version running on server: %s\n", client.version()["Version"])

        client.containers.run('python', 'python -c \"{}\"'.format(code))