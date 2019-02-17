flask_port=$1
if [[ -z ${flask_port} ]]
then
   flask_port=6500
fi

virtualenv_path="$2"
if [[ -z ${virtualenv_path} ]]
then
   virtualenv_path="/opt/Virtualenvs3/dashrisk"
fi

workspace="$3"
if [[ -z ${workspace} ]]
then
   workspace="/root/pyliverisk"
fi

mip=$(ifconfig|grep -A 1 eth0 | grep inet|egrep -o "addr[:][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}"|egrep -o "[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}")
source ${virtualenv_path}/bin/activate
cd ${workspace}/dashrisk/dashrisk
python3 -i dash_risk_grid.py --ip ${mip} --port ${flask_port}
cd ~
deactivate
