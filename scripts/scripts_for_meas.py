import numpy as np
import pickle
import math
import matplotlib.pyplot as plt
import os
import argparse
from scipy.interpolate import interp1d
from drivers.spec_drivers import select_spec_driver
from drivers.gen_drivers import select_gen_driver
from drivers.board_drivers import select_board_driver

class meas:
    def __init__(self, b, g, s):
        self.b = b
        self.g = g
        self.s = s

    def meas_cable(self, farray, name_txt, name_pickle):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        BASE_DIR = os.path.dirname(SCRIPT_DIR)
        calibrovka_d = []
        span = 0.1
        rbw = 0.001
        level = 0
        att = 20

        self.g.gen_freq_level(farray[0], level)
        self.s.set_meas_off()
        self.s.spec_cent_span_rbw_att(farray[0], span, rbw, att)
        self.g.gen_ON()
        for f in farray:
            self.s.spec_cent(f)
            self.g.gen_freq(f)
            loss = - float(self.s.peak_search() - level)
            calibrovka_d.append([float(f), loss])
            print(f'freq = {f} -> loss = {round(loss,2)} dB')
        self.g.gen_OFF()
        self.s.set_cont_sweep()

        name_dir = os.path.join(BASE_DIR, 'calib_cables')
        if os.path.exists(name_dir) and os.path.isdir(name_dir):
            print(f"Директория '{name_dir}' уже существует.")
        else:
            os.makedirs(name_dir)  # создаёт все недостающие родительские папки
            print(f"Директория '{name_dir}' создана.")

        file_path_txt = f'{name_dir}\\' + name_txt
        file_path = f'{name_dir}\\' + name_pickle
        np.savetxt(file_path_txt, np.array(calibrovka_d), fmt='%0.2f', delimiter='\t')

        f_d = [row[0] for row in calibrovka_d]
        calib_d = [row[1] for row in calibrovka_d]
        loss_cable = interp1d(f_d, calib_d, kind='nearest')

        with open(file_path, 'wb') as f_calib:
            pickle.dump(loss_cable, f_calib)

        print(f'\nИзмерение РЧ кабеля успешно выполнено!\n')

        f_plot = np.arange(farray[0], farray[-1], 1)
        calib = loss_cable(f_plot)
        plt.plot(f_d, calib_d, 'bo', label='Измеренные точки')  # синие точки
        plt.plot(f_plot, calib, 'r-', label='Интерполяция')  # красная линия
        plt.grid()
        plt.title('Ослабление кабеля')
        plt.xlabel('Частота, МГц')
        plt.ylabel('Потери, дБ')
        plt.legend()
        plt.show()

    def measONE_NF(self, f, intbw, level, name_cableIN_pickle):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        BASE_DIR = os.path.dirname(SCRIPT_DIR)
        path_calibIN = os.path.join(BASE_DIR, 'calib_cables', name_cableIN_pickle)
        # path_calibIN = 'calib_cables\\' + name_cableIN_pickle
        with open(path_calibIN, 'rb') as file_calib:  # загрузка ослабления
            loss_cableIN = pickle.load(file_calib)  # входного кабеля
        k = 1.38 * 10 ** (-23)  # Дж/К - Постоянная Больцмана
        N0 = k * 300  # ДЖ = ВТ*с - СПМ теплового шума
        self.g.gen_OFF()
        self.s.spec_cent(f)
        q1_db = self.s.CHP_meas()  # измер. мощ-ти собст. шумов на выходе RX
        q1 = (10 ** (q1_db / 10))  # перевод дБмВт в мВт
        self.g.gen_freq_level(f, level)
        self.g.gen_ON()
        q2_db = self.s.CHP_meas()  # измер. мощ-ти собст. шумов + сигнал на вых RX
        q2 = (10 ** (q2_db / 10))  # перевод дБмВт в мВт
        We = 10 ** ((level - loss_cableIN(f) - 30) / 10) / (intbw * 1e6)  # СПМ сигн. на входе RX
        NF = 10 * math.log10(q1 / (q2 - q1) * We / N0)  # Оценка КШ
        self.g.gen_OFF()
        return np.round(NF, 1)

    def meas_NF(self, farray, name_pickle):
        '''
        Методы power_ON/OFF выступают заглушками
        Подключите выход ГС ко входу АС через входной РЧ кабель
        Тогда результат измерения покажет собственные шумы АС
        '''
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        BASE_DIR = os.path.dirname(SCRIPT_DIR)

        span = 0.042  # MHz
        rbw = 0.0001  # MHz: Соотношение span/rbw лучше делать 100
        att = 0  # dB
        intbw = 0.042  # MHz
        level = -60  # дБмВт на выходе ГС
        self.s.set_CHP_mode(farray[0], span, rbw, att, intbw)
        NF_full_table = []
        self.b.power_ON()
        for f in farray:
            NF = m.measONE_NF(f, intbw, level, name_pickle)
            NF_full_table.append([f, NF])
            print(f'freq = {f} -> NF = {round(NF, 1)} dB')
        self.b.power_OFF()
        self.s.set_cont_sweep()
        self.s.set_meas_off()
        name_dir = os.path.join(BASE_DIR, 'results')
        # name_dir = 'results'
        if os.path.exists(name_dir) and os.path.isdir(name_dir):
            print(f"Директория '{name_dir}' уже существует.")
        else:
            os.makedirs(name_dir)  # создаёт все недостающие родительские папки
            print(f"Директория '{name_dir}' создана.")

        file_path = f'{name_dir}\\nf_meas.txt'
        with open(file_path, 'w') as file:
            file.write('\t|'.join(map(str, ['f,MHz', 'NF,dB\n'])))
            for line in NF_full_table:
                file.write('\t|\t'.join(map(str, line)) + '\n')

        f_d = [item[0] for item in NF_full_table]
        NF_d = [item[1] for item in NF_full_table]

        print(f'\nИзмерение КШ успешно выполнено!\n')

        plt.plot(f_d, NF_d, 'bo', label='Измеренные значения')  # синие точки
        plt.grid()
        plt.title('Измеренный КШ')
        plt.xlabel('Частота, МГц')
        plt.ylabel('КШ, дБ')
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Автоматизированные измерения: калибровка кабеля или оценка КШ'
    )
    parser.add_argument(
        '--calibrate',
        action='store_true',
        help='Запустить измерение ослабления РЧ кабеля (калибровку)'
    )
    parser.add_argument(
        '--nf',
        action='store_true',
        help='Запустить измерение коэффициента шума'
    )
    args = parser.parse_args()

    # Если не указан ни один флаг — выводим справку
    args.calibrate = True
    args.nf = True
    if not args.calibrate and not args.nf:
        parser.print_help()
        exit(1)

    b = select_board_driver()
    g = select_gen_driver('192.168.1.23')
    s = select_spec_driver('192.168.1.24')

    if (b == False) or (g == False) or (s == False):
        print('Обеспечьте корректное подключение стенда')
    else:
        m = meas(b, g, s)

        if args.calibrate:
            print('\n=== Запуск калибровки кабеля ===\n')
            m.meas_cable(
                farray=np.arange(950, 2151, 10),
                name_txt='loss_cableIN.txt',
                name_pickle='loss_cableIN.pickle'
            )

        if args.nf:
            print('\n=== Запуск измерения КШ ===\n')
            m.meas_NF(
                farray=np.arange(950, 2151, 50),
                name_pickle='loss_cableIN.pickle'
            )


