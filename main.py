import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# v2 -> v3

DB = "library.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, author TEXT, genre TEXT, year INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS readers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fio TEXT, phone TEXT, address TEXT, category TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reader_id INTEGER, book_id INTEGER,
        issue_date TEXT, return_date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT, password TEXT, role TEXT)""")
    conn.commit()
    conn.close()

class TableWindow(tk.Toplevel):
    def __init__(self, master, table, columns):
        super().__init__(master)
        self.title(f"Таблица: {table}")
        self.geometry("800x500")
        self.table = table
        self.columns = columns

        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        frame = tk.Frame(self)
        frame.pack(pady=5)
        self.entries = {}
        for i, col in enumerate(columns):
            if col == "id":
                continue
            tk.Label(frame, text=col).grid(row=0, column=i, padx=3)
            e = tk.Entry(frame, width=15)
            e.grid(row=1, column=i, padx=3)
            self.entries[col] = e

        btns = tk.Frame(self)
        btns.pack(pady=10)
        tk.Button(btns, text="Добавить", width=12, command=self.add).pack(side="left", padx=5)
        tk.Button(btns, text="Редактировать", width=14, command=self.edit).pack(side="left", padx=5)
        tk.Button(btns, text="Удалить", width=12, command=self.delete).pack(side="left", padx=5)
        tk.Button(btns, text="Обновить", width=12, command=self.load).pack(side="left", padx=5)
        tk.Button(btns, text="В PDF", width=10, command=self.export_pdf).pack(side="left", padx=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.load()

    def load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(f"SELECT * FROM {self.table}")
        for row in c.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        for col, val in zip(self.columns, values):
            if col in self.entries:
                self.entries[col].delete(0, tk.END)
                self.entries[col].insert(0, val)

    def add(self):
        data = [self.entries[c].get() for c in self.columns if c != "id"]
        if not all(data):
            messagebox.showwarning("Ошибка", "Заполни все поля")
            return
        placeholders = ",".join("?" * len(data))
        cols = ",".join(c for c in self.columns if c != "id")
        conn = sqlite3.connect(DB)
        conn.execute(f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders})", data)
        conn.commit()
        conn.close()
        self.load()
        self.clear()

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Ошибка", "Выбери строку")
            return
        row_id = self.tree.item(sel[0], "values")[0]
        data = [self.entries[c].get() for c in self.columns if c != "id"]
        cols = [c for c in self.columns if c != "id"]
        sets = ",".join(f"{c}=?" for c in cols)
        conn = sqlite3.connect(DB)
        conn.execute(f"UPDATE {self.table} SET {sets} WHERE id=?", data + [row_id])
        conn.commit()
        conn.close()
        self.load()
        self.clear()

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Ошибка", "Выбери строку")
            return
        row_id = self.tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Подтверждение", "Удалить строку?"):
            return
        conn = sqlite3.connect(DB)
        conn.execute(f"DELETE FROM {self.table} WHERE id=?", (row_id,))
        conn.commit()
        conn.close()
        self.load()
        self.clear()

    def clear(self):
        for e in self.entries.values():
            e.delete(0, tk.END)

    def export_pdf(self):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        pdfmetrics.registerFont(TTFont('DejaVu', "DejaVuSans.ttf"))

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(f"SELECT * FROM {self.table}")
        rows = c.fetchall()
        conn.close()

        pdf = canvas.Canvas(f"{self.table}.pdf", pagesize=landscape(A4))
        width, height = landscape(A4)
        y = height - 40
        pdf.setFont("DejaVu", 10)
        pdf.drawString(30, y, " | ".join(self.columns))
        y -= 20
        for row in rows:
            pdf.drawString(60, y, " | ".join(str(v) for v in row))
            y -= 18
            if y < 40:
                pdf.showPage()
                y = height - 40
        pdf.save()
        messagebox.showinfo("Готово", f"Сохранено в {self.table}.pdf")

class QueryWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Запросы")
        self.geometry("900x500")

        self.queries = {
            "1. Все книги": ("SELECT * FROM books", []),
            "2. Все читатели": ("SELECT * FROM readers", []),
            "3. Все выдачи": ("SELECT * FROM loans", []),
            "4. Книги по жанру (параметр)": (
                "SELECT * FROM books WHERE genre = ?", ["Жанр"]),
            "5. Читатели по категории (параметр)": (
                "SELECT * FROM readers WHERE category = ?", ["Категория"]),
            "6. Выдачи по читателю (параметр)": (
                "SELECT l.id, r.fio, b.title, l.issue_date "
                "FROM loans l "
                "JOIN readers r ON l.reader_id = r.id "
                "JOIN books b ON l.book_id = b.id "
                "WHERE r.fio = ?", ["ФИО читателя"]),
        }

        tk.Label(self, text="Выбери запрос:").pack()
        self.combo = ttk.Combobox(self, values=list(self.queries.keys()), width=40)
        self.combo.pack(pady=5)
        self.combo.bind("<<ComboboxSelected>>", self.on_select)

        self.param_frame = tk.Frame(self)
        self.param_frame.pack(pady=5)
        self.param_entry = None

        tk.Button(self, text="Выполнить", command=self.run).pack(pady=5)

        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_select(self, event):
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entry = None
        name = self.combo.get()
        params = self.queries[name][1]
        if params:
            tk.Label(self.param_frame, text=params[0] + ":").pack(side="left")
            self.param_entry = tk.Entry(self.param_frame)
            self.param_entry.pack(side="left")

    def run(self):
        name = self.combo.get()
        if not name:
            return
        sql, params = self.queries[name]
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        if params:
            val = self.param_entry.get()
            if not val:
                messagebox.showwarning("Ошибка", "Введи параметр")
                return
            c.execute(sql, (val,))
        else:
            c.execute(sql)
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        conn.close()

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        for row in rows:
            self.tree.insert("", "end", values=row)

def main():
    init_db()
    root = tk.Tk()
    root.title("ИС Библиотека")
    root.geometry("400x400")

    tk.Label(root, text="Информационная система\n«Библиотека»",
             font=("Arial", 14, "bold")).pack(pady=20)

    tables = {
        "Книги": ("books", ["id", "title", "author", "genre", "year"]),
        "Читатели": ("readers", ["id", "fio", "phone", "address", "category"]),
        "Выдача": ("loans", ["id", "reader_id", "book_id", "issue_date", "return_date"]),
        "Пользователи": ("users", ["id", "login", "password", "role"]),
    }

    for name, (table, cols) in tables.items():
        tk.Button(root, text=name, width=25,
                  command=lambda t=table, c=cols: TableWindow(root, t, c)).pack(pady=5)

    tk.Button(root, text="Запросы", width=25,
              command=lambda: QueryWindow(root)).pack(pady=15)

    root.mainloop()

if __name__ == "__main__":
    main()
