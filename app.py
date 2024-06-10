import subprocess, os, re
from datetime import datetime, timedelta
from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import IntegerField, SubmitField, SelectField, BooleanField, RadioField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler


FOLDER = os.path.basename(os.path.dirname(os.path.abspath(__file__))) + '/'
app = Flask(__name__, static_folder=os.getcwd())
app.config.from_pyfile('config.py')
bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
app.app_context().push()


class Sessions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    terrain = db.Column(db.String)
    img = db.Column(db.String)

    def __init__(self, timestamp, terrain, img):
        self.timestamp = timestamp
        self.terrain = terrain
        self.img = img


def delete_expired():
    day_ago = datetime.now() - timedelta(days=1)
    with app.app_context():
        q = Sessions.query.filter(Sessions.timestamp < day_ago)
        files = q.with_entities(Sessions.terrain, Sessions.img).all()
        for t, i in files:
            if os.path.exists(t):
                os.remove(t)
            if os.path.exists(i):
                os.remove(i)        
        q.delete()
        db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_expired, trigger='interval', days=1)
scheduler.start()


def parse_res(str):
    data = str.decode('utf-8')

    result = {}

    pattern = re.compile(r'(.+?) = ([\d.]+(?: secs| J| times| bytes|))')
    matches = pattern.findall(data)
    for match in matches:
        key, value = match
        result[key.strip()] = value

    gw_pattern = re.compile(r'GW (\w+) sent out (\d+) acks and commands')
    gw_matches = gw_pattern.findall(data)
    gw_list = []
    for gw, value in gw_matches:
        gw_list.append((f'Gateway {gw}', value))
    result['GW'] = gw_list

    node_pattern = re.compile(r'# of nodes with SF(\d+): (\d+), Avg retransmissions: ([\d.]+)')
    node_matches = node_pattern.findall(data)
    sf_list = []
    for sf, num_nodes, avg_retrans in node_matches:
        sf_list.append((f'SF{sf}', num_nodes, avg_retrans))
    result['SF'] = sf_list

    return result


class SimulationForm(FlaskForm):
    frequency = RadioField('Frequency Plan', choices=[('eu', 'EU868'), ('us', 'US915')], validators=[DataRequired()], default='eu', id='freq')
    packets_per_hour = IntegerField('Packets per hour ', validators=[DataRequired(), NumberRange(min=1, max=1800)], default=10)
    auto_simtime = BooleanField('Auto Simulation Time', id='auto_sim')
    simulation_time = IntegerField('Simulation Time (hours)', default=1, validators=[DataRequired(), NumberRange(min=1, max=240)], id='sim')
    ack_policy = SelectField('Acknowledgement Policy', choices=[('1', 'First-Come First-Served (RCFS)'), ('2', 'Best Received Signal Strength Indicator (RSSI)'), ('3', 'Least busy Gateway')], validators=[DataRequired()], id='policy', default='1')
    max_retr = IntegerField('Max Retries', validators=[DataRequired(), NumberRange(min=1, max=8),], default=8)
    channels = SelectField('Number of Channels', choices=[('3', '3'), ('8', '8')], validators=[DataRequired()], default='8')
    rx2sf = IntegerField('RX2 SF', validators=[DataRequired(), NumberRange(min=7, max=12)], default=7, id='channels')
    fixed_packet_size = BooleanField('Fixed Packet Size', id = 'fixed')
    packet_size = IntegerField('Average Packet Size', validators=[NumberRange(min=1, max=50)], default=16, id='size')
    packet_size_distr = SelectField('Packet Size Distribution', choices=[('normal', 'Normal'), ('uniform', 'Uniform')], id = 'distr', default='normal')
    confirmed_perc = IntegerField('Percentage of EDs that require an ACK', validators=[InputRequired(), NumberRange(min=0, max=100)], default=100)
    submit = SubmitField('Simulate')


class TerrainForm(FlaskForm):
    size = IntegerField('Terrain Side Length', validators=[DataRequired(), NumberRange(min=100)], default='1000')
    nodes = IntegerField('Number of Nodes', default='100', validators=[DataRequired(), NumberRange(min=1, max=5000)])
    gateways = IntegerField('Number of Gateways', default='2', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Generate')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = TerrainForm()
    message = ''
    if form.validate_on_submit():
        size = form.size.data
        nodes = form.nodes.data
        gateways = form.gateways.data
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d-%H-%M-%S.%f')
        file = 'terrains/' + timestamp_str + '.txt'
        img_file = 'imgs/' + timestamp_str + '.png'
        try:
            subprocess.run(['perl generate_terrain.pl ' + str(size) + ' ' + str(nodes) + ' ' + str(gateways) + ' > ' + file], shell=True)
            subprocess.run(['perl draw_terrain.pl' + ' ' + file + ' ' + img_file], shell=True)
            new_session = Sessions(timestamp, file, img_file)
            db.session.add(new_session)
            db.session.commit()
            session['id'] = new_session.id
            img_file = FOLDER + img_file
        except subprocess.CalledProcessError as e:
            img_file = FOLDER + 'static/imgs/error_placeholder.png'
            message = e
        except Exception as e:
            message = e
    else:
        img_file = None
    return render_template('index.html', form=form, message=message, img_file=img_file, tab='Generate')


@app.route('/simulate', methods=['GET', 'POST'])
def simulate():
    form = SimulationForm()
    message = ''
    img_file = None
    if session['id']:
        user_session = Sessions.query.get(session['id'])
        file = user_session.terrain
        img_file = FOLDER + user_session.img
    else:
        return redirect(url_for(''))
    
    if form.validate_on_submit():
        packets_per_hour = form.packets_per_hour.data
        simulation_time = form.simulation_time.data
        ack_policy = form.ack_policy.data
        max_retr = form.max_retr.data
        channels = form.channels.data
        rx2sf = form.rx2sf.data
        fixed_packet_size = 0 if form.fixed_packet_size.data == False else 1
        packet_size_distr = form.packet_size_distr.data
        auto_simtime = 0 if form.auto_simtime.data == False else 1
        packet_size = form.packet_size.data
        confirmed_perc = form.confirmed_perc.data / 100
        if form.frequency.data == 'eu':
            script_name = 'LoRaWAN.pl'
        else: 
            script_name = 'LoRaWAN-US915.pl'
            simulation_time = round(simulation_time*3600)
        if os.path.exists(file): 
            try:
                res = subprocess.check_output(['perl ' + script_name + ' ' + str(packets_per_hour) + ' ' + str(simulation_time) + ' ' + str(ack_policy) + ' ' + str(max_retr) + ' ' + str(channels) + ' ' + str(rx2sf) + ' ' + str(fixed_packet_size) + ' ' + str(packet_size_distr) + ' ' + str(auto_simtime) + ' ' + str(packet_size) + ' ' + str(confirmed_perc) + ' ' + file], shell=True, timeout=30)
                session['result'] = parse_res(res)
            except subprocess.CalledProcessError as e:
                message = e
            except Exception as e:
                message = e
    else:
        session['result'] = None
    return render_template('index.html', form=form, message=message, result=session['result'], img_file=img_file, tab="Simulate")