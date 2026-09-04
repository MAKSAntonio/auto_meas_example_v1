import socket
from drivers.scpi_device import SCPIdevice


class GenBase(SCPIdevice):
    COMMAND_MAP = {
        'freq': (':FREQ {value} MHz;', ':FREQ?;', None),
        'level': (':POW:LEV {value} DBM;', ':POW:LEV?;', None),
        'on': (':OUTP ON;', ':OUTP?;', 1),
        'off': (':OUTP OFF;', ':OUTP?;', 0)
    }

    def __init__(self, host):
        self.host = host
        self.temp = SCPIdevice(self.host, 5025)

    def _set_param(self, cmd_template, value, query_template=None, target=None):
        set_cmd = cmd_template.format(value=value)
        query_cmd = query_template.format(value=value) if query_template else None
        self.temp.wait_for_setting(set_cmd, query_cmd, target)

    def gen_freq(self, freq_mhz): # установка частоты гармонического сигнала
        cmd_set, cmd_query, _ = self.COMMAND_MAP['freq']
        self._set_param(cmd_set, freq_mhz, cmd_query, int(freq_mhz * 1e6))

    def gen_level(self, level_dbm): # установка мощности выходного сигнала
        cmd_set, cmd_query, target = self.COMMAND_MAP['level']
        self._set_param(cmd_set, level_dbm, cmd_query, target)

    def gen_ON(self):
        cmd_set, cmd_query, target = self.COMMAND_MAP['on']
        self.temp.wait_for_setting(cmd_set, cmd_query, target)

    def gen_OFF(self):
        cmd_set, cmd_query, target = self.COMMAND_MAP['off']
        self.temp.wait_for_setting(cmd_set, cmd_query, target)

    def gen_freq_level(self, FREQ, LEVEL):
        self.gen_freq(FREQ)
        self.gen_level(LEVEL)

def select_gen_driver(host, port=5025):
    # Проверяем, есть ли пинг
    try:
        socket.create_connection((host, port), timeout=1) # Проверяем, есть ли Ethernet соединение
        return GenBase(host)

    except (socket.timeout, socket.error):
        print('Не подключен генератор с IP ' + str(host))
        return False

if __name__ == '__main__':
    '''Запустить для проверки соединения с генератором сигналов'''
    g = select_gen_driver(host='192.168.1.23')

    if g != False:
        g.gen_ON()
        g.gen_freq_level(1050, -50)
        g.gen_OFF()
