import subprocess, datetime, os, re
from flask import Flask, render_template, redirect, session
from flask_bootstrap import Bootstrap5
from flask_session import Session
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import IntegerField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, NumberRange

app = Flask(__name__, static_folder=os.getcwd())
app.secret_key = 'tO$&!|0wkamvVia0?n$NqIRVWOG'
bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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
    # simulator = SelectField('Protocol', choices=[('eu', 'EU868'), ('us', 'US915')], validators=[DataRequired()])
    packets_per_hour = IntegerField('Packets per hour ', validators=[DataRequired(), NumberRange(min=1)], default=10)
    auto_simtime = BooleanField('Auto Simulation Time', id="auto_sim")
    simulation_time = IntegerField('Simulation Time (s)', default=3600, validators=[DataRequired(), NumberRange(min=3600)], id="sim")
    ack_policy = SelectField('Acknowledgement Policy', choices=[('1', 'First-Come First-Served (RCFS)'), ('2', 'Best Received Signal Strength Indicator (RSSI)'), ('3', 'Least busy Gateway')], validators=[DataRequired()])
    max_retr = IntegerField('Max Retries', validators=[DataRequired(), NumberRange(min=1, max=8),], default=8)
    channels = SelectField('Number of Channels', choices=[('3', '3'), ('8', '8')], validators=[DataRequired()], default='8')
    rx2sf = IntegerField('RX2 SF', validators=[DataRequired(), NumberRange(min=7, max=12)], default=7)
    fixed_packet_size = BooleanField('Fixed Packet Size', id = "fixed")
    packet_size = IntegerField('Average Packet Size', validators=[NumberRange(min=1, max=50)], default=16, id="size")
    packet_size_distr = SelectField('Packet Size Distribution', choices=[('normal', 'Normal'), ('uniform', 'Uniform')], id = "distr", default='normal')
    confirmed_perc = IntegerField('Percentage of EDs that require an ACK', validators=[DataRequired(), NumberRange(min=0, max=100)], default=100)
    submit = SubmitField('Simulate')

class TerrainForm(FlaskForm):
    size = IntegerField('Terrain Size', validators=[DataRequired(), NumberRange(min=100)], default="1000")
    nodes = IntegerField('Number of Nodes', default="100", validators=[DataRequired(), NumberRange(min=1)])
    gateways = IntegerField('Number of Gateways', default="2", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Generate')

@app.route("/", methods=['GET', 'POST'])
def index():
    form = TerrainForm()
    message = ""
    if form.validate_on_submit():
        size = form.size.data
        nodes = form.nodes.data
        gateways = form.gateways.data
        session["id"] = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S.%f")
        file = "terrains\\" + session["id"] + ".txt"
        img_file = "imgs\\" + session["id"] + ".png"
        try:
            subprocess.run(["perl", "generate_terrain.pl", str(size), str(nodes), str(gateways), ">", "terrains\\" + session["id"] + ".txt"], shell=True)
            subprocess.run(["perl", "draw_terrain.pl", file, img_file], shell=True)
            session["image"] = "website/imgs/" + session["id"] + ".png"
        except Exception as e:
            message = e
        return redirect("/simulate")
    else:
        session["image"] = None
    return render_template('index.html', form=form, message=message, tab="Generate")

@app.route("/simulate", methods=['GET', 'POST'])
def simulate():
    form = SimulationForm()
    message = ""
    
    if form.validate_on_submit():
        # form.submit
        packets_per_hour = form.packets_per_hour.data
        simulation_time = form.simulation_time.data
        ack_policy = form.ack_policy.data
        max_retr = form.max_retr.data
        channels = form.channels.data
        rx2sf = form.rx2sf.data
        if form.fixed_packet_size.data:
            form.packet_size.label.text = "Packet Size"
            form.packet_size_distr.render_kw = {'disabled': 'disabled'}
        else:
            form.packet_size.label.text = "Average Packet Size"
        fixed_packet_size = 0 if form.fixed_packet_size.data == False else 1
        packet_size_distr = form.packet_size_distr.data
        auto_simtime = 0 if form.auto_simtime.data == False else 1
        packet_size = form.packet_size.data
        confirmed_perc = form.confirmed_perc.data / 100
        # device = "LoRaWAN.pl" if form.simulator.data == 'eu' else "LoRaWAN-US915.pl"
        if session["id"]:
            file = "terrains\\" + session["id"] + ".txt"
            if os.path.exists(file): 
                try:
                    res = subprocess.check_output(["perl", "LoRaWAN.pl", str(packets_per_hour), str(simulation_time), str(ack_policy), "terrains\\" + session["id"] + ".txt", str(max_retr), str(channels), str(rx2sf), str(fixed_packet_size), str(packet_size_distr), str(auto_simtime), str(packet_size), str(confirmed_perc)], shell=True)
                    session["result"] = parse_res(res)
                except Exception as e:
                    message = e
    else:
        session["result"] = None
    return render_template('index.html', form=form, message=message, result=session["result"], img_file=session["image"], tab="Simulate")