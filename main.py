from camera import Camera
from code_executor import CodeExecutor

picture = Camera().capture()
code = picture.get_code()
CodeExecutor().execute_code(code)