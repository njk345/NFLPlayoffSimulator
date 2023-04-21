from flask import Flask, render_template, request
from datetime import datetime
from nflsim import sim_season

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        year = int(request.form['year'])
        start_week = datetime.strptime(request.form['start_week'], "%Y-%m-%d")
        epochs = int(request.form['epochs'])
        results = sim_season(year, start_week, epochs)
        return render_template('index.html', results=results.table_repr())
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
