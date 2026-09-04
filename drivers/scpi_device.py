import socket
import logging
import time

class SCPIdevice:

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def send(self, cmds, do_receive=None):
        """Отправляет команду и ждет ответ, если do_receive"""
        if not self.host:
            raise Exception(f"{self.title}: не установлен IP")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host.encode('ASCII'), self.port))
                for cmd in cmds:
                    s.sendall((cmd + "\n").encode('ASCII'))
                return (s.recv(1024)) if do_receive else None
        except Exception as e:
            logging.error(f"({self.host}): ошибка отправки команды.\n{e}")
            return False


    def wait_for_setting(self, set_cmd, query_cmd, target, attempts=5, delay=0.1):
        """Отправляет команду и проверяет (если нужно) ответ по query_cmd.
        Повторяет attempts раз, чтобы убедиться, что прибор принял настройку."""
        for attempt in range(attempts):
            self.send([set_cmd])
            if target is None:
                return True
            response = self.send([query_cmd], do_receive=1)
            if response is None:
                time.sleep(delay)
                continue
            try:
                if isinstance(target, str):
                    current = str(response.decode().strip())
                    if target in current:
                        return True
                else:
                    current = float(response.decode().strip())
                    if abs(current - target) < 1e-9:
                        return True
            except ValueError:
                pass
            time.sleep(delay)
        logging.warning(f"Не удалось установить значение {target} за {attempts} попыток. ")
        raise RuntimeError(f"Не удалось установить {target} за {attempts} попыток")