# -*- coding: utf-8 -*-
__author__ = "Alban", "Audrey", "Alexandre"

from ivy.std_api import IvyBindMsg
from ivy.std_api import IvySendMsg
import time
import logging
import pyrejeu.models as mod
import utils
import math
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=mod.engine)

class RejeuClock(object):

    def __init__(self, start_time=0):
        self.running = True
        self.paused = True
        self.current_time = start_time
        self.rate = 1.0
        self.session = Session()
        # abonnement aux messages relatifs à l'horloge
        self.__set_subscriptions()

    def __set_subscriptions(self):
        IvyBindMsg(lambda *l: self.start(), '^ClockStart')
        IvyBindMsg(lambda *l: self.stop(), '^ClockStop')
        IvyBindMsg(lambda *l: self.modify_rate(l[1]), '^SetClock Rate=(\S+)')
        IvyBindMsg(lambda *l: self.modify_init_time(l[1]), '^SetClock Time=(\S+)')
        IvyBindMsg(lambda *l: self.send_beacons(l[1]), "^GetAllBeacons MsgName=(\S+)")
        IvyBindMsg(lambda *l: self.send_pln(l[1], int(l[2]), l[3]), "^GetPln MsgName=(\S+) Flight=(\S+) From=(\S+)")
        IvyBindMsg(lambda *l: self.send_sectors_info(l[1], int(l[2])), "^GetSectorsInfos MsgName=(\S+) Flight=(\S+)")


    def main_loop(self):
        # Envoi des infos de début et de fin de la simulation
        list_flights = self.session.query(mod.Flight)
        (start_time, stop_time) = utils.extract_sim_bounds(list_flights)

        msg_rangeupdate = "RangeUpdateEvent FirstTime=%s LastTime=%s" % (
            utils.sec_to_str(start_time), utils.sec_to_str(stop_time))
        logging.debug(msg_rangeupdate)
        IvySendMsg(msg_rangeupdate)

        #Boucle d'horloge
        while self.running:
            if self.paused:
                # en pause, on ne doit plus faire avancer l'horloge
                # et émettre les messages
                time.sleep(0.1)
                continue

            logging.debug("Loop running, SimTime=%s" \
                    % utils.sec_to_str(self.current_time))
            IvySendMsg("ClockEvent Time=%s Rate=%d Bs=0" \
                    % (utils.sec_to_str(self.current_time), self.rate))

            # récupérer les plots à envoyer
            list_cones = self.session.query(mod.Cone) \
                                     .filter(mod.Cone.hour == self.current_time)

            # pour chaque plot
            for cone in list_cones:
                g_speed = math.sqrt((cone.vit_x)**2+(cone.vit_y)**2)
                heading = utils.get_heading(cone.vit_x, cone.vit_y)
                msg = "TrackMovedEvent Flight=%d CallSign=%s Ssr=%d Sector=-- Layers=F X=%f Y=%f Vx=%d Vy=%d Afl=%d Rate=%d Heading=%d GroundSpeed=%d Tendency=%d Time=%s" %\
                      ( cone.flight.id, cone.flight.callsign, cone.flight.ssr, cone.pos_x/60, cone.pos_y/60, cone.vit_x, cone.vit_y, cone.flight_level, cone.rate, heading,int(g_speed), cone.tendency, utils.sec_to_str(cone.hour) )
                #logging.debug("Message envoye : %s" % msg)
                IvySendMsg(msg)

            IvySendMsg("EndTransmissionEvent Time=%s" % (utils.sec_to_str(self.current_time)))

            if self.rate>0 :
                self.current_time += 1
                time.sleep(1.0 / self.rate)
            else :
                self.current_time -=1
                time.sleep(-1.0 / self.rate)


    def stop(self):
        logging.debug("Clock Stopped")
        self.paused = True

    def start(self):
        logging.debug("Clock Started")
        self.paused = False

    def close(self):
        self.running = False

    def modify_rate(self, rate_value):
        logging.debug("SetClock")
        self.rate = int(rate_value)

    def modify_init_time(self, init_time):
        logging.debug("Set Init Time")
        self.current_time = utils.str_to_sec(init_time)

    def send_beacons(self, msg_name):
        l_beacons = self.session.query(mod.Beacon)
        count = 0
        msg = "AllBeacons %s Slice=" % (msg_name)
        for beacon in l_beacons:
            msg += beacon.display_beacon() + " "
            count += 1
            if count == 50:
                IvySendMsg(msg.strip())
                count = 0
                msg = "AllBeacons %s Slice=" % (msg_name)
        if count > 0:
            IvySendMsg(msg)
        IvySendMsg("AllBeacons %s EndSlice" % msg_name)

    def send_pln(self, msg_name, flight_id, init_order):
        flight = self.session.query(mod.Flight).filter(mod.Flight.id == flight_id).first()
        if init_order == "now":
            starting_time = self.current_time
            starting_beacon = None
        elif init_order == "origin":
            starting_beacon = None
            starting_time = None
        elif len(init_order.split(':'))>1:
            starting_beacon = None
            starting_time = utils.str_to_sec(init_order)
        else :
            starting_beacon = init_order
            starting_time = None
        route = utils.extract_route(flight.flight_plan, starting_beacon, starting_time)
        msg_pln = "Pln %s Flight=%d Time=%s CallSign=%s AircraftType=%s Ssr=%d Speed=%d Rfl=%d Dep=%s Arr=%s Rvsm=%s Tcas=%s Adsb=%s DLink=%s List=%s" % \
                        (msg_name, flight.id, utils.sec_to_str(self.current_time), flight.callsign, flight.type, flight.ssr, flight.v, flight.fl, flight.dep, flight.arr,
                         flight.rvsm, flight.tcas, flight.adsb, flight.dlink, route.strip())
        flight.pln_event = 1
        IvySendMsg(msg_pln)

    def send_sectors_info(self, msg_name, flight_id):
        msg = "SectorsInfo %s Flight=%d List=--" % (msg_name, flight_id)
        IvySendMsg(msg)



