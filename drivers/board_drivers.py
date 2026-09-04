def select_board_driver():
    return BoardBase()

class BoardBase:
    def power_ON(self):
        print('power ON')

    def power_OFF(self):
        print('power OFF')
