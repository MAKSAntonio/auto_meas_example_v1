import logging
import socket
from drivers.scpi_device import SCPIdevice



class SpecBase(SCPIdevice):  # Базовый класс драйвера
    # Словарь команд – каждая модель анализатора переопределяет под себя
    COMMAND_MAP = {
        'mode_sa': None,  # установка режима АС
        'meas_off': None,  # выключение любых режимов измерения
        'meas_chp': None,  # включение режима измерение мощности в полосе (CHP)
        'cent_freq': None,  # установка центральной частоты
        'span': None,  # установка полосы обзора
        'rbw': None,  # установка полосы разрешения
        'att': None,  # установка входного аттенюатора
        'intbw': None,  # установка полосы интегрирования в режиме CHP
        'preamp_on': None,  # включение предусилителя
        'preamp_off': None,  # выключение предусилителя АС
        'peak_y': None,  # поиск пика
        'peak_x': None,  # поиск частоты пика
        'min_peak_y': None,  # поиск минимума
        'cont_peak_on': None,  # непрерывное слежение за максимумом
        'chp_read': None,  # чтение мощности в полосе в режиме CHP
        'avg_on': None,  # включить усреднение проходов
        'avg_count': None,  # число проходов усреднения
        'avg_off': None,  # выключить усреднение проходов
        'sweep_single': None,  # включить одиночное свипирование
        'sweep_cont': None,  # включить непрерывное свипирование
    }

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def _set_param(self, cmd_template, value, query_template=None, target=None):
        set_cmd = cmd_template.format(value=value)
        query_cmd = query_template.format(value=value) if query_template else None
        self.wait_for_setting(set_cmd, query_cmd, target)

    def set_mode_sa(self):  # Установка режима АС
        cmd_set, cmd_query, target = self.COMMAND_MAP['mode_sa']
        if cmd_set is None:
            print(f'{self.__class__.__name__} в режиме SA по умолчанию')
            return
        self.wait_for_setting(set_cmd=cmd_set, query_cmd=cmd_query, target=target)

    def set_meas_off(self):  # выключение любых режимов измерения (например, CHP)
        cmd_set, cmd_query, target = self.COMMAND_MAP['meas_off']
        self.wait_for_setting(set_cmd=cmd_set, query_cmd=cmd_query, target=target)

    def set_meas_chp(self):  # включение режима измерение мощности в полосе (CHP)
        cmd_set, cmd_query, target = self.COMMAND_MAP['meas_chp']
        self.wait_for_setting(set_cmd=cmd_set, query_cmd=cmd_query, target=target)

    def spec_cent(self, freq_mhz):  # Установка центральной частоты
        cmd_set, cmd_query, _ = self.COMMAND_MAP['cent_freq']
        self._set_param(cmd_set, freq_mhz, cmd_query, int(freq_mhz * 1e6))

    def spec_span(self, freq_span_mhz):  # Установка полосы обзора
        cmd_set, cmd_query, _ = self.COMMAND_MAP['span']
        self._set_param(cmd_set, freq_span_mhz, cmd_query, None)

    def spec_rbw(self, rbw_mhz):  # Установка полосы разрешения
        cmd_set, cmd_query, _ = self.COMMAND_MAP['rbw']
        self._set_param(cmd_set, rbw_mhz, cmd_query, None)

    def spec_att(self, att_db):  # Установка входного аттенюатора
        cmd_set, cmd_query, _ = self.COMMAND_MAP['att']
        self._set_param(cmd_set, att_db, cmd_query, None)

    # Установка полосы интегрирования в режиме CHP
    def spec_intbw(self, intbw_mhz):
        cmd_set, cmd_query, _ = self.COMMAND_MAP['intbw']
        self._set_param(cmd_set, intbw_mhz, cmd_query, None)

    def preamp_on(self):  # Включение предусилителя
        cmd_set, cmd_query, target = self.COMMAND_MAP['preamp_on']
        if cmd_set is None:
            raise RuntimeError(f'{self.__class__.__name__} не поддерживает предусилитель')
        self.wait_for_setting(set_cmd=cmd_set, query_cmd=cmd_query, target=target)

    def preamp_off(self):  # Выключение предусилителя
        cmd_set, cmd_query, target = self.COMMAND_MAP['preamp_off']
        if cmd_set is None:
            return  # Нет предусилителя – просто выходим
        self.wait_for_setting(set_cmd=cmd_set, query_cmd=cmd_query, target=target)

    def prepare_single_sweep(self):  # включить одиночное свипирование
        self.send([self.COMMAND_MAP['sweep_single'], '*OPC?'], do_receive=1)

    def set_cont_sweep(self):  # включить непрерывное свипирование
        self.send([self.COMMAND_MAP['sweep_cont']])

    def peak_search(self):  # Поиск пика с запросом
        self.prepare_single_sweep()
        cmd = self.COMMAND_MAP['peak_y']
        result = self.send([cmd], do_receive=1)
        return float(result.decode()) if result else None

    def peak_search_freq(self):  # Поиск частоты пика
        self.prepare_single_sweep()
        cmd = self.COMMAND_MAP['peak_x']
        result = self.send([cmd], do_receive=1)
        return float(result.decode()) if result else None

    def min_search(self):  # Поиск следующего пика
        self.prepare_single_sweep()
        cmd = self.COMMAND_MAP['min_peak_y']
        result = self.send([cmd], do_receive=1)
        return float(result.decode()) if result else None

    def set_cont_peak_on(self):  # Установка следящего peak_search
        cmd = self.COMMAND_MAP['cont_peak_on']
        if cmd == None:
            print(f'{self.__class__.__name__} не поддерживает функцию следящего поиска максимума')
            return
        self.send([cmd], do_receive=0)

    def CHP_meas(self):  # Измерение мощности в полосе intbw в режиме CHP
        avg_on_cmd = self.COMMAND_MAP['avg_on']
        avg_cnt_cmd = self.COMMAND_MAP['avg_count']  # усреднение 5 раз
        self.send([avg_on_cmd, avg_cnt_cmd])
        # i = 0
        # while i < 6:  # Ожидание усреднения
        #     i += 1
        #     self.prepare_single_sweep()
        self.prepare_single_sweep()
        read_cmd = self.COMMAND_MAP['chp_read']
        result = self.send([read_cmd], do_receive=1)
        avg_off_cmd = self.COMMAND_MAP['avg_off']
        self.send([avg_off_cmd])
        if result:
            return float(result.decode().split(',')[0])
        return None

    def spec_cent_span_rbw_att(self, freq_cent, freq_span, rbw, att):
        self.set_meas_off()
        self.preamp_off()
        self.spec_cent(freq_cent)
        self.spec_span(freq_span)
        self.spec_rbw(rbw)
        self.spec_att(att)

    def set_CHP_mode(self, freq_cent, freq_span, rbw, att, intbw):
        self.set_meas_chp()
        # self.preamp_on()
        self.spec_cent(freq_cent)
        self.spec_intbw(intbw)
        self.spec_span(freq_span)
        self.spec_rbw(rbw)
        self.spec_att(att)


class Akip4212Driver(SpecBase):
    COMMAND_MAP = {
        'mode_sa': (None, None, None),
        'meas_off': (':INST:MEAS OFF;', ':INST:MEAS?;', 'OFF'),
        'meas_chp': (':INST:MEAS CHP;', ':INST:MEAS?;', 'CHP'),
        'cent_freq': (':FREQ:CENT {value} MHz;', ':FREQ:CENT?;', None),
        'span': (':FREQ:SPAN {value} MHz;', ':FREQ:SPAN?;', None),
        'rbw': (':BAND:RES {value} MHz;', ':BAND:RES?;', None),
        'att': (':POW:ATT {value} DB;', ':POW:ATT?;', None),
        'intbw': (':CHP:BWID:INT {value} MHz;', ':CHP:BWID:INT?;', None),
        'preamp_on': (':POW:GAIN ON;', ':POW:GAIN?;', 1),
        'preamp_off': (':POW:GAIN OFF;', ':POW:GAIN?;', 0),
        'peak_y': ':CALC:MARK1:MAX; :CALC:MARK1:Y?',
        'peak_x': ':CALC:MARK1:MAX; :CALC:MARK1:X?',
        'min_peak_y': ':CALC:MARK2:MIN; :CALC:MARK2:Y?',
        'cont_peak_on': ':CALC:MARK1:CPEak ON',
        'chp_read': ':MEAS:CHP:CHP?',
        'avg_on': ':AVER:TRAC1:STAT ON',
        'avg_count': 'AVER:TRAC:COUNt 5',
        'avg_off': 'AVER:TRAC:COUNt 1',
        'sweep_single': ':INIT:CONT OFF; :INIT:IMM',
        'sweep_cont': ':INIT:CONT ON',
    }

class KeysightN9952ADriver(SpecBase):
    COMMAND_MAP = {
        'mode_sa': ('INST "SA";', 'INST?;', 'SA'),
        'meas_off': (':SENS:MEAS:CHAN NONE;', ':SENS:MEAS:CHAN?;', 'NONE'),
        'meas_chp': (':SENSe:MEAS:CHAN CHP;', ':SENSe:MEAS:CHAN?;', 'CHP'),
        'cent_freq': (':SENS:FREQ:CENTer {value} MHZ;', ':SENS:FREQ:CENT?;', None),
        'span': (':SENS:FREQ:SPAN {value} MHZ;', ':SENSe:FREQ:SPAN?;', None),
        'rbw': (':SENS:BAND:RES {value} MHZ;', ':SENS:BAND:RES?;', None),
        'att': (':SENS:POW:RF:ATT {value} DB;', ':SENS:POW:RF:ATT?;', None),
        'intbw': (':SENS:CME:IBW {value} MHZ', ':SENSe:CME:IBW?;', None),
        'preamp_on': (':SENS:POW:RF:GAIN ON;', ':SENS:POW:RF:GAIN?;', 1),
        'preamp_off': (':SENS:POW:RF:GAIN OFF;', ':SENS:POW:RF:GAIN?;', 0),
        'peak_y': ':CALC:MARK1:FUNCTION:MAX; :CALC:MARK1:Y?',
        'peak_x': ':CALC:MARKer1:FUNCTION:MAX; :CALC:MARKer1:X?',
        'min_peak_y': ':CALC:MARK2:FUNC:MIN; :CALC:MARK2:Y?',
        'cont_peak_on': None,
        'chp_read': ':CALC:MEAS:DATA?',
        'avg_on': ':CME:AVER:ENAB ON',
        'avg_count': ':SENS:AVER:COUN 5',
        'avg_off': ':SENS:AVER:COUN 1',
        'sweep_single': ':INIT:CONT OFF; :INIT:IMM',
        'sweep_cont': ':INIT:CONT ON',
    }
    def spec_att(self, att_db):
        """Переопределение метода: ограничение аттенюатора для N9952A"""
        if att_db > 30:
            att_db = 30
            logging.error('Макс. значение ATT для Keysight N9952A равно 30 дБ')
        super().spec_att(att_db)

class Akip4214Driver(SpecBase):
    COMMAND_MAP = {
        'mode_sa': (None, None, None),
        'meas_off': (':INSTrument:MEASure SA;', ':INSTrument:MEASure?;', 'SA'),
        'meas_chp': (':INSTrument:MEASure CHP;', ':INSTrument:MEASure?;', 'CHP'),
        'cent_freq': (':FREQ:CENT {value} MHz;', ':FREQ:CENT?;', None),
        'span': (':FREQ:SPAN {value} MHz;', ':FREQ:SPAN?;', None),
        'rbw': (':BAND:RES {value} MHz;', ':BAND:RES?;', None),
        'att': (':POW:ATT {value} DB;', ':POW:ATT?;', None),
        'intbw': (':CHP:BWID:INT {value} MHz;', ':CHP:BWID:INT?;', None),
        'preamp_on': (None, None, None),
        'preamp_off': (':POW:GAIN OFF;', ':POW:GAIN?;', 0),
        'peak_y': ':CALC:MARK1:STAT ON; :CALC:MARK1:MAX; :CALC:MARK1:Y?;',#\n:CALC:MARK1:MAX; :CALC:MARK1:Y?',
        'peak_x': ':CALC:MARK1:STAT ON; :CALC:MARK1:MAX; :CALC:MARK1:Y?;',#\n:CALC:MARK1:MAX; :CALC:MARK1:X?',
        'next_peak_y': ':CALC:MARK2:STAT ON; :CALC:MARK2:MIN; :CALC:MARK2:Y?',#':CALC:MARK2:MAX; :CALC:MARK2:Y?;\n:CALC:MARK2:MAX:NEXT; :CALC:MARK2:Y?',
        'cont_peak_on': ':CALCulate:MARKer1:CPEak ON',
        'chp_read': ':MEAS:CHPower:CHPower?',
        'avg_on': ':CME:AVERage:ENABle ON',
        'avg_count': ':SENSe:AVERage:COUNt 5',
        'avg_off': ':SENSe:AVERage:COUNt 1',
        'sweep_single': ':INIT:CONT OFF; :INIT:IMM',  # для разных вендоров может отличаться
        'sweep_cont': ':INIT:CONT ON',
    }

    def peak_search(self): # Поиск пика
        self.prepare_single_sweep()
        self.send([':CALC:MARK1:MAX;'])
        result = self.send([':CALC:MARK1:MAX; :CALC:MARK1:Y?;'], do_receive=1)
        return float(result.decode()) if result else None

    def peak_search_freq(self): # Поиск частоты пика
        self.prepare_single_sweep()
        self.send([':CALC:MARK1:MAX;']) # При первом запросе должен включиться
        result = self.send([':CALC:MARK1:MAX; :CALC:MARK1:X?;'], do_receive=1)
        return float(result.decode()) if result else None

    def next_peak_search(self): # Поиск следующего пика
        self.prepare_single_sweep()
        self.send([':CALC:MARK2:MIN;']) # При первом запросе должен включиться
        result = self.send([':CALC:MARK2:MIN; :CALC:MARK2:Y?'], do_receive=1)
        return float(result.decode()) if result else None

DRIVER_CLASSES = [
    Akip4212Driver,
    KeysightN9952ADriver,
    Akip4214Driver
]
IDN_MAP = {
    'Akip': Akip4212Driver,
    'Keysight': KeysightN9952ADriver,
    'Vendor YSA001 13.6G': Akip4214Driver, # пример нестандартного ответа
}
def select_spec_driver(host, port=5025):
    try:
        socket.create_connection((host, port), timeout=1)
        temp_driver = SCPIdevice(host, port)
        idn_response = temp_driver.send(['*IDN?'], do_receive=1).decode().split(',')[0]
        if idn_response == 'Vendor':
            idn_response = temp_driver.send(['*IDN?'], do_receive=1).decode().split(',')[0:2]
            idn_response = idn_response[0] + ' ' + idn_response[1]
        print(f"Получен *IDN?: {idn_response}")
        for keyword, driver_class in IDN_MAP.items():
            if keyword.lower() in idn_response.lower():
                print(f"Обнаружен прибор: {keyword}")
                inst = driver_class(host, port)
                inst.set_mode_sa()
                return inst
        print(f"Неизвестный прибор: {idn_response}. Используем первый драйвер.")
        inst = DRIVER_CLASSES[0](host, port)
        inst.set_mode_sa()
        return inst
    except (socket.timeout, socket.error):
        print(f"Не удалось подключиться к {host}:{port}")
        return False

if __name__ == '__main__':
    '''Запустить для проверки соединения с анализатором спектра'''
    s = select_spec_driver(host='192.168.1.24') # Автоматически подбираем драйвер

    if s != False:
        s.set_mode_sa() # Перевод в режим анализатора спектра

        # s.set_meas_chp() # Включение измерение CHP
        # s.set_CHP_mode(freq_cent=501, freq_span=0.60, rbw=0.0001, att=0, intbw=0.42)
        # print(f'CHP = {s.CHP_meas()} dBm')

        s.set_meas_off() # Выключение всех измерений

        s.spec_cent(freq_mhz=1001)
        s.spec_span(freq_span_mhz=10)
        s.spec_rbw(rbw_mhz=0.1)
        s.spec_att(att_db=30)

        # s.spec_cent_span_rbw_att(freq_cent=224, freq_span=1, rbw=0.01, att=20)

        # s.preamp_on()
        s.preamp_off()

        print(f'peak_search = {s.peak_search()} dBm')
        s.set_cont_sweep()
