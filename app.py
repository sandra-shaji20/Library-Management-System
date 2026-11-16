from flask import Flask, request, redirect, url_for, flash, render_template_string
import sqlite3
from pathlib import Path
from datetime import date

app=Flask(__name__)
app.secret_key="local-development-key-change-before-deployment"
DB=Path(__file__).with_name("library.db")
TABLE="books"
FIELDS=['title', 'author', 'isbn', 'total', 'available']

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL, author TEXT NOT NULL, isbn TEXT NOT NULL UNIQUE, total INTEGER NOT NULL, available INTEGER NOT NULL)")

        c.execute("CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,book_id INTEGER,borrower TEXT,issue_date TEXT,return_date TEXT)")

@app.route("/")
def index():
    q=request.args.get("q","").strip()
    where=" OR ".join([f"{f} LIKE ?" for f in FIELDS[:3]])
    with db() as c:
        rows=c.execute(f"SELECT * FROM {TABLE} WHERE {where} ORDER BY id DESC",tuple([f"%{q}%"]*min(3,len(FIELDS)))).fetchall()
        count=c.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        if TABLE=="products":
            low=c.execute("SELECT COUNT(*) FROM products WHERE quantity<=reorder_level").fetchone()[0]
            units=c.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        else: low=units=0

        with db() as c:
            transactions=c.execute("SELECT t.*,b.title FROM transactions t JOIN books b ON b.id=t.book_id ORDER BY t.id DESC").fetchall()

    body="""<div class='toolbar'><h2>Records</h2><a class='btn' href='{{ url_for("add") }}'>+ Add new</a></div>
    <div class='card'><p>Total records: <b>{{ count }}</b>"""

    body += """<form class='toolbar' method='get'><input name='q' placeholder='Search records' value='{{ q }}'><button>Search</button></form><div class='wrap'><table><tr>"""
    for f in FIELDS: body += f"<th>{{f.replace('_',' ').title()}}</th>"
    body += "<th>Actions</th></tr>{% for r in rows %}<tr>"
    for f in FIELDS: body += f"<td>{{{{r['{f}']}}}}</td>"
    body += """<td><a class='btn secondary' href='{{ url_for("edit",rid=r["id"]) }}'>Edit</a>
    <form style='display:inline' method='post' action='{{ url_for("delete",rid=r["id"]) }}'><button class='danger'>Delete</button></form>"""
    body += """<a class='btn' href='{{ url_for("issue",rid=r["id"]) }}'>Issue</a>"""

    body += "</td></tr>{% else %}<tr><td colspan='20'>No records found.</td></tr>{% endfor %}</table></div></div>"

    body += """<div class='card'><h2>Issue / return transactions</h2><div class='wrap'><table><tr><th>Book</th><th>Borrower</th><th>Issued</th><th>Returned</th><th>Action</th></tr>{% for t in transactions %}<tr><td>{{t.title}}</td><td>{{t.borrower}}</td><td>{{t.issue_date}}</td><td>{{t.return_date or "—"}}</td><td>{% if not t.return_date %}<form method='post' action='{{url_for("return_book",tid=t.id)}}'><button>Return</button></form>{% endif %}</td></tr>{% endfor %}</table></div></div>"""

    return render_template_string(LAYOUT,title=TITLE,subtitle=SUBTITLE,body=render_template_string(body,rows=rows,count=count,q=q,low=low,units=units,transactions=transactions))

@app.route("/add",methods=["GET","POST"])
def add():
    if request.method=="POST":
        vals=[request.form.get(f,"").strip() for f in FIELDS]
        try:
            with db() as c: c.execute(f"INSERT INTO {{TABLE}}({','.join(FIELDS)}) VALUES({','.join(['?']*len(FIELDS))})",vals)
            flash("Record added successfully."); return redirect(url_for("index"))
        except sqlite3.IntegrityError: flash("A unique field already exists or the supplied data is invalid.")
    return form(None)

@app.route("/edit/<int:rid>",methods=["GET","POST"])
def edit(rid):
    with db() as c: item=c.execute(f"SELECT * FROM {{TABLE}} WHERE id=?",(rid,)).fetchone()
    if not item: return "Record not found",404
    if request.method=="POST":
        vals=[request.form.get(f,"").strip() for f in FIELDS]
        try:
            with db() as c: c.execute(f"UPDATE {{TABLE}} SET "+",".join([f+"=?" for f in FIELDS])+" WHERE id=?",(*vals,rid))
            flash("Record updated."); return redirect(url_for("index"))
        except sqlite3.IntegrityError: flash("Unique field already exists or data is invalid.")
    return form(item)

def form(item):
    body="""<div class='card'><h2>{{ 'Edit' if item else 'Add' }} record</h2><form method='post'>"""
    for f in FIELDS:
        body+=f"<label>{{f.replace('_',' ').title()}}</label><input name='{{f}}' required value='{{{{ item['{{f}}'] if item else '' }}}}'>"
    body+="""<button>Save</button> <a class='btn secondary' href='{{url_for("index")}}'>Cancel</a></form></div>"""
    return render_template_string(LAYOUT,title=TITLE,subtitle=SUBTITLE,body=render_template_string(body,item=item))

@app.post("/delete/<int:rid>")
def delete(rid):
    with db() as c: c.execute(f"DELETE FROM {{TABLE}} WHERE id=?",(rid,))
    flash("Record deleted."); return redirect(url_for("index"))

@app.route("/issue/<int:rid>",methods=["GET","POST"])
def issue(rid):
    with db() as c: book=c.execute("SELECT * FROM books WHERE id=?",(rid,)).fetchone()
    if not book: return "Book not found",404
    if request.method=="POST":
        borrower=request.form.get("borrower","").strip()
        if book["available"]<1: flash("No copies available.")
        elif borrower:
            with db() as c:
                c.execute("UPDATE books SET available=available-1 WHERE id=?",(rid,))
                c.execute("INSERT INTO transactions(book_id,borrower,issue_date) VALUES(?,?,?)",(rid,borrower,date.today().isoformat()))
            flash("Book issued."); return redirect(url_for("index"))
    body="""<div class='card'><h2>Issue {{book.title}}</h2><p>Available copies: {{book.available}}</p><form method='post'><label>Borrower name</label><input name='borrower' required><button {% if book.available<1 %}disabled{% endif %}>Issue</button></form></div>"""
    return render_template_string(LAYOUT,title=TITLE,subtitle=SUBTITLE,body=render_template_string(body,book=book))

@app.post("/return/<int:tid>")
def return_book(tid):
    with db() as c:
        t=c.execute("SELECT * FROM transactions WHERE id=?",(tid,)).fetchone()
        if t and not t["return_date"]:
            c.execute("UPDATE transactions SET return_date=? WHERE id=?",(date.today().isoformat(),tid))
            c.execute("UPDATE books SET available=available+1 WHERE id=?",(t["book_id"],))
    flash("Return processed."); return redirect(url_for("index"))

TITLE='Library Management System'
SUBTITLE='Manage books and issue/return transactions'
LAYOUT='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }}</title><link rel="stylesheet" href="{{ url_for(\'static\',filename=\'style.css\') }}"></head><body><header><h1>{{ title }}</h1><p>{{ subtitle }}</p></header><main>{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="flash">{{ m }}</div>{% endfor %}{% endwith %}{{ body|safe }}</main></body></html>'
init_db()
if __name__=="__main__": app.run(debug=True)
