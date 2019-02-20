'''
Created on Feb 17, 2019

schedule daily updates to database from yahoo

@author: bperlman1
'''
import sys
from distutils.command.build import build
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')
from dashrisk import schedule_it
from dashrisk import build_history
import argparse as ap
import time


if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument('--hour',type=int,help='hour to start database update',default='1')
    parser.add_argument('--username',type=str,
                    help='username (None will be postgres)',
                    nargs='?')
    parser.add_argument('--password',type=str,
                    help='password (None will be blank)',
                    nargs='?')
    args = parser.parse_args()
    h = args.hour
    logger = schedule_it.init_root_logger("logfile.log", "INFO")
    while True:
        logger.info(f"scheduling update for hour {h}")
        schedule_it.ScheduleNext('hour', h,logger = logger)
        logger.info(f"updating history")
        bh = build_history.HistoryBuilder(update_table=True,username=args.username,password=args.password,logger=logger)
        bh.execute()
#         bh.update_yahoo_daily()
        logger.info(f"sleeping for an hour before next scheduling")
        time.sleep(60*60)
        