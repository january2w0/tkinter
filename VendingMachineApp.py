import os
from functools import partial
from tkinter import *
from tkinter import ttk
from tkinter import messagebox, simpledialog
from dataclasses import dataclass

# DPI 인식 활성화
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1)

# ----- 음료수 데이터 클래스 -----
@dataclass
class Drink:
    name: str = ""
    price: int = 0
    stock: int = 10
    image_path: str = ""

# ----- 자판기 로직 클래스 -----
class VendingMachine:
    def __init__(self):
        self.balance = 0
        self.total_sales = 0
        self.max_slots = 15
        self.drinks, self.cash_storage = self.load_file("drinks.txt", "cash.txt")
        self.password = "0000"

    # ─── 파일 정보 읽기 ───────────────────────────────────
    def load_file(self, drinks_file: str, cash_file: str) -> (list[Drink], dict[int, int]):
        # 음료 정보 읽기
        drinks: list[Drink] = [ Drink() for _ in range(self.max_slots) ]
        with open(drinks_file, "r") as file:
            for i, line in enumerate(file):
                name, price, stock, image_path = line.strip().split(", ")
                drinks[i] = Drink(name, int(price), int(stock), image_path)

        # 현금 정보 읽기
        cash: dict[int, int] = {}
        with open(cash_file, "r") as file:
            for line in file:
                coin, stock = line.strip().split(": ")
                cash[int(coin)] = int(stock)
        return drinks, cash

    # ─── 파일 정보 저장 ───────────────────────────────────
    def save_file(self, drinks_file: str, cash_file: str) -> None:
        # 음료 정보 쓰기
        with open(drinks_file, "w") as file:
            for drink in self.drinks:
                file.write(f"{drink.name}, {drink.price}, {drink.stock}, {drink.image_path}\n")

        # 현금 정보 쓰기
        with open(cash_file, "w") as file:
            for coin, count in self.cash_storage.items():
                file.write(f"{coin}: {count}\n")

    # ─── 현금 투입 ───────────────────────────────────
    def insert_money(self, amount: dict[int, int]) -> None:
        for coin, count in amount.items():
            self.balance += coin * count
            self.cash_storage[coin] += count

    def can_buy(self, drink: Drink) -> bool:
        return self.balance >= drink.price and (drink.stock > 0 and drink.price != 0)

    # ─── 음료 구매 ───────────────────────────────────
    def buy_drink(self, drink: Drink) -> None:
        if self.can_buy(drink):
            self.balance -= drink.price
            drink.stock -= 1
            self.total_sales += drink.price

    # ─── 잔돈 반환 ───────────────────────────────────
    def refund(self) -> dict[int, int]:
        remainder = self.balance
        change: dict[int, int] = {}
        for coin in self.cash_storage.keys():
            count = min(remainder // coin, self.cash_storage[coin])  # 기계에 남아 있는 만큼 또는 필요한 만큼만
            if count:
                change[coin] = count
                remainder -= coin * count
        if remainder != 0:  # 잔돈 반환 실패
            return {}
        for coin, count in change.items():
            self.cash_storage[coin] -= count
        self.balance = 0
        return change

    # ─── 상태 읽기 ───────────────────────────────────
    def get_status(self) -> (str, bool):
        if not self.drinks[0].name:
            return "음료 없음", DISABLED
        if not any(count > 10 for count in self.cash_storage.values()):
            return "동전 없음", DISABLED
        return "판매중", NORMAL

# ----- GUI 클래스 -----
class VendingMachineApp:
    def __init__(self, root):
        self.root = root
        self.root.title("자판기 프로그램")
        self.root.geometry("1000x1400")
        self.root.resizable(False, False)
        self.vm = VendingMachine()
        self.insert_popup = None  # 현금 투입 팝업(Toplevel) 참조

        # 음료 위젯
        self.drink_buttons = []
        self.drink_entries = []

        # 메인 프레임
        self.consumer_frame = Frame(self.root, bg="sea green")
        self.admin_frame = Frame(self.root, bg="#E5E5E5")

        # UI 생성
        self.build_consumer_ui()
        self.build_admin_ui()
        self.show_consumer()

    def create_slots(self, parent: Frame, mode: str):
        for index, drink in enumerate(self.vm.drinks):
            # 한 슬롯의 전체 프레임
            slot = Frame(parent, width=160, height=300, relief="flat", bg="lightgray", borderwidth=1)
            slot.grid(row=index // 5, column=index % 5, padx=10)
            slot.pack_propagate(False)

            # 사진과 글자를 담는 프레임
            panel = ttk.Frame(slot, relief="raised")
            panel.pack(fill="x", pady=10)

            img = PhotoImage(file=drink.image_path) if os.path.exists(drink.image_path) else PhotoImage(width=130, height=130)
            img_label = Label(panel, image=img, width=130, height=130); img_label.image = img
            img_label.pack()

            # 글자만 담은 프레임
            content = Frame(panel, relief="raised", bg="light cyan")
            content.pack(fill="x")

            Label(content, text=drink.name, bg="light cyan").pack()
            Label(content, text=f"{drink.price}원", bg="light cyan").pack()

            # 모드에 따라 구분
            if mode == "buy":
                button = ttk.Button(slot, text="구매", command=partial(self.handle_buy, drink))
                button.pack(pady=10)
                self.drink_buttons.append(button)
            elif mode == "stock" and drink.name:
                entry = ttk.Entry(slot, width=5, justify="center")
                entry.insert(0, str(drink.stock))
                entry.pack()
                self.drink_entries.append(entry)

    # ─── 소비자 모드 UI 생성 ───────────────────────────────────
    def build_consumer_ui(self):
        # 1. 음료 슬롯 프레임
        self.drink_frame = Frame(self.consumer_frame, bg="lightgray")
        self.create_slots(self.drink_frame, "buy")
        self.drink_frame.pack(ipadx=5, ipady=5, pady=40)

        # 하단 제어 프레임
        button_frame = Frame(self.consumer_frame, bg="sea green")
        button_frame.pack()

        # 2. 광고판 프레임
        ad_panel = Frame(button_frame, width=330, height=170, bg="white")
        ad_panel.pack(padx=(40, 20), side='left')
        ad_panel.pack_propagate(False)
        img = PhotoImage(file="ad.gif") if os.path.exists("ad.gif") else PhotoImage(width=330, height=170)
        img_label = Label(ad_panel, image=img); img_label.image = img
        img_label.pack()

        # 3. 제어판 프레임
        control_panel = Frame(button_frame, width=530, height=170, bg="#54C888")
        control_panel.pack(padx=(20, 40), side='left')
        control_panel.pack_propagate(False)

        # 반환 버튼
        sub1 = Frame(control_panel, bg="#333333")
        sub1.pack(side='left', padx=10)
        self.status_label = Label(sub1, text="판매중\n237895", fg="tomato", bg="#333333")
        self.status_label.pack(pady=7)
        self.refund_button = ttk.Button(sub1, text="반환", command=self.handle_refund)
        self.refund_button.pack()

        # 입금 버튼
        sub2 = Frame(control_panel)
        sub2.pack(side='left', padx=10)
        img = PhotoImage(file="coin.gif") if os.path.exists("coin.gif") else PhotoImage(width=80, height=80)
        img_label = Label(sub2, image=img); img_label.image = img
        img_label.pack()
        self.insert_button = ttk.Button(sub2, text="입금", command=self.open_insert_money)
        self.insert_button.pack()

        # 모드 전환 버튼
        sub3 = Frame(control_panel)
        sub3.pack(side='left', padx=10)
        img = PhotoImage(file="key.gif") if os.path.exists("key.gif") else PhotoImage(width=80, height=80)
        img_label = Label(sub3, image=img); img_label.image = img
        img_label.pack()
        ttk.Button(sub3, text="관리", command=self.show_admin).pack()

        # 4. 배출구 프레임
        exit_panel = Frame(self.consumer_frame, width=600, height=150, relief="raised", bg='white')
        exit_panel.pack(pady=(40, 50))
        exit_panel.pack_propagate(False)
        inner = Frame(exit_panel, width=585, height=135, bg="#B0B0B0")
        inner.place(relx=0.5, rely=0.5, anchor='center')

    # ─── 관리자 모드 UI 생성 ───────────────────────────────────
    def build_admin_ui(self):
        # 1. 음료 슬롯 프레임
        stock_frame = Frame(self.admin_frame, bg="lightgray")
        self.create_slots(stock_frame, "stock")
        stock_frame.pack(ipadx=5, ipady=5, pady=40)

        # 하단 제어 프레임
        button_frame = Frame(self.admin_frame, bg="#E5E5E5")
        button_frame.pack()

        # 2. 동전 재고 관리 프레임
        cash_panel = Frame(button_frame, width=330, height=170, bg="lightgray")
        cash_panel.pack(padx=(40, 20), side='left')
        cash_panel.pack_propagate(False)
        Label(cash_panel, text="[잔돈 재고]", bg="lightgray").grid(row=0, column=0, columnspan=4, pady=10)
        self.cash_entries = []
        for i, coin in enumerate(self.vm.cash_storage.keys()):
            ttk.Label(cash_panel, text=f"{coin}원").grid(row=1, column=i)
            cash_entry = ttk.Entry(cash_panel, width=5, justify="center")
            cash_entry.insert(0, str(self.vm.cash_storage[coin]))
            cash_entry.grid(row=2, column=i, padx=10, pady=15)
            self.cash_entries.append(cash_entry)

        # 3. 제어판 프레임
        control_panel = Frame(button_frame, width=530, height=170, bg="lightgray")
        control_panel.pack(padx=(20, 40), side='left')
        control_panel.pack_propagate(False)

        # 수익금 표시
        sub1 = Frame(control_panel, bg="#333333")
        sub1.pack(side='left', padx=10)
        self.sales_label = Label(sub1, text=f"수익금\n{self.vm.total_sales}", fg="tomato", bg="#333333")
        self.sales_label.pack(padx=30, pady=7)

        # 저장 버튼
        sub2 = Frame(control_panel)
        sub2.pack(side='left', padx=10)
        img = PhotoImage(file="save.gif") if os.path.exists("save.gif") else PhotoImage(width=80, height=80)
        img_label = Label(sub2, image=img); img_label.image = img
        img_label.pack()
        ttk.Button(sub2, text="저장", command=self.save_stock).pack()

        # 모드 전환 버튼
        sub3 = Frame(control_panel)
        sub3.pack(side='left', padx=10)
        img = PhotoImage(file="key.gif") if os.path.exists("key.gif") else PhotoImage(width=80, height=80)
        img_label = Label(sub3, image=img); img_label.image = img
        img_label.pack()
        ttk.Button(sub3, text="메인", command=self.show_consumer).pack()

        # 4. 배출구 프레임
        exit_panel = Frame(self.admin_frame, width=600, height=150, relief="raised", bg='white')
        exit_panel.pack(pady=(40, 50))
        exit_panel.pack_propagate(False)
        inner = Frame(exit_panel, width=585, height=135, bg="gray")
        inner.place(relx=0.5, rely=0.5, anchor='center')

    # ─── UI 갱신 ───────────────────────────────────
    def update_ui(self):
        # 소비자 모드 갱신
        status, enabled = self.vm.get_status()
        self.status_label["text"] = f"{status}\n{self.vm.balance}"
        self.insert_button["state"] = self.refund_button["state"] = enabled
        for drink, button in zip(self.vm.drinks, self.drink_buttons):
            button["state"] = enabled if self.vm.can_buy(drink) else DISABLED

        # 관리자 모드 갱신
        self.sales_label["text"] = f"수익금\n{self.vm.total_sales}"
        for drink, entry in zip(self.vm.drinks, self.drink_entries):
            if entry:
                entry.delete(0, END)
                entry.insert(0, str(drink.stock))
        for entry, coin in zip(self.cash_entries, self.vm.cash_storage.keys()):
            entry.delete(0, END)
            entry.insert(0, str(self.vm.cash_storage[coin]))

    # ─── 입금 버튼 이벤트 ───────────────────────────────────
    def open_insert_money(self):
        # 팝업이 이미 켜져 있으면 무시
        if self.insert_popup:
            return
        popup = Toplevel(self.root)
        popup.title("현금 투입")
        popup.resizable(False, False)
        self.insert_popup = popup

        insert_cash: dict[int, int] = {1000: 0, 500: 0, 100: 0, 50: 0}

        # 현금 버튼 이벤트
        def add_amt(coin):
            insert_cash[coin] += 1
            cash_label["text"] = str(sum(k * v for k, v in insert_cash.items()))

        # 확인 버튼 이벤트
        def confirm():
            self.vm.insert_money(insert_cash)
            self.update_ui()
            popup.destroy()
            self.insert_popup = None

        # 현금 버튼 / 입금량 표시 / 확인 버튼
        for i, coin in enumerate(self.vm.cash_storage.keys()):
            ttk.Button(popup, text=f"{coin}원", command=partial(add_amt, coin)).grid(row=0, column=i, padx=10, pady=20)
        cash_label = Label(popup, text="0", fg="tomato", bg="#333333")
        cash_label.grid(row=1, column=0, columnspan=4, ipadx=10)
        ttk.Button(popup, text="확인", command=confirm).grid(row=2, column=0, columnspan=4, pady=20)

        popup.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, 'insert_popup', None), popup.destroy()))

    # ─── 구매 버튼 이벤트 ───────────────────────────────────
    def handle_buy(self, drink: Drink):
        self.vm.buy_drink(drink)
        messagebox.showinfo("구매 완료", f"{drink.name}을(를) 구매하셨습니다.")
        self.update_ui()

    # ─── 반환 버튼 이벤트 ───────────────────────────────────
    def handle_refund(self):
        change = self.vm.refund()
        if change:
            msg = "  [거스름돈]\n" + "\n".join([ f"{coin}원 x {count}개" for coin, count in change.items() ])
            messagebox.showinfo("환전 완료", msg)
            self.update_ui()
        else:
            messagebox.showwarning("환전 불가", "거스름돈을 제공할 수 없습니다.")

    # ─── 저장 버튼 이벤트 ───────────────────────────────────
    def save_stock(self):
        for drink, entry in zip(self.vm.drinks, self.drink_entries):
            drink.stock = int(entry.get())
        for entry, coin in zip(self.cash_entries, self.vm.cash_storage.keys()):
            self.vm.cash_storage[coin] = int(entry.get())
        self.vm.save_file("drinks.txt", "cash.txt")
        messagebox.showinfo("업데이트 완료", "재고가 갱신되었습니다.")

    def show_consumer(self):
        self.admin_frame.pack_forget()
        self.consumer_frame.pack(fill="both", expand=True)
        self.update_ui()

    def show_admin(self):
        pw = simpledialog.askstring("관리자 모드", "비밀번호를 입력하세요.", show='*')
        if pw == self.vm.password:
            self.consumer_frame.pack_forget()
            self.admin_frame.pack(fill="both", expand=True)
            self.update_ui()
        else:
            messagebox.showerror("오류", "비밀번호가 틀렸습니다.")

# ----- 메인 실행부 -----
if __name__ == "__main__":
    window = Tk()
    app = VendingMachineApp(window)
    window.mainloop()
