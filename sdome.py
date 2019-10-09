#!/usr/bin/python3
# -*- encoding: utf8 -*-

##### MODULES EXTERNES #####
import sys
import socket
import time
#import threading
# Firmata
from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants
board = PyMata3(com_port='/dev/ttyUSB1')

CMD=''
PORTEOUV=False
POSDOME=False

# Entrées/sorties
MOTEUR=11	
ALIMMOT=10	
ALIM12=9	
ALIMTEL=8	
P11=7		
P12=6		
P21=5		
P22=4

# Délais
DPORTES=40
DPORTESCAPTEURS=30
DMOTEUR=40
DABRI=20

##### FONCTIONS #####
def PStatus(pin):
	if pin<16:
		return board.get_pin_state(pin)[2]
	else:
		return board.digital_read(pin)
def Pwrite(pin, etat):
	board.digital_write(pin, etat)
def Pinit(pin,mode):
	board.set_pin_mode(pin, mode)
		
def AlimStatus():
	return not PStatus(ALIMTEL)
def MoteurStatus():
	return not PStatus(ALIMMOT)
def StartTel():
	Pwrite(ALIMTEL,0)
def StopTel():
	Pwrite(ALIMTEL,1)
def StartMot():
	Pwrite(ALIMMOT,0)
def StopMot(): 
	Pwrite(ALIMMOT,1)

def Attend(delai):
	time.sleep(delai)
	
def FermePorte1():
	Pwrite(P11,0)
	time.sleep(DPORTES)
	Pwrite(P11,1)
	
def OuvrePorte1():
	Pwrite(P12,0)
	time.sleep(DPORTES)
	Pwrite(P12,1)
	
def CmdTelnet():
	global conn
	try:
		conn, addr = s.accept()
		CMD = conn.recv(32)
	except BlockingIOError:
		return ''
	else:
		return CMD
				
def EnvoiStatus(ret):
	conn.sendall(str(int(ret)).encode('utf8'))

def EnvoiMsg(ret):
	conn.sendall(str(ret).encode('utf8'))
	
def EnvoiCommande(cmd):
	global CMD
	global conn
	CMD=CMD[:2]
	print(CMD)
	# Exécute la commande
	if CMD==b'D+':
		EnvoiStatus(OuvreDome())
	elif CMD==b"D-":
		FermeDome()
	elif CMD==b'P+':
		EnvoiStatus(OuvrePortes())
	elif CMD==b'P-':
		EnvoiStatus(FermePortes())
	elif CMD==b'A+':
		StartTel()
		EnvoiStatus('1')
	elif CMD==b'A-':
		StopTel()
		EnvoiStatus('0')
	elif CMD==b'A?':
		EnvoiStatus(AlimStatus())
	elif CMD==b'p-':
		FermePorte1()
	elif CMD==b'p+':
		OuvrePorte1()
	elif CMD==b'C?':
		EnvoiStatus(AlimStatus())
	conn.close()

def Debug(message):
	# Affiche les informations
	print(message)
	
def OuvrePortes():
	global PORTEOUV
	if PORTEOUV:
		# Les portes sont déjà ouvertes
		return 0
	StartMot()
	Debug('Ouverture des portes...')
	Pwrite(P12,0)
	Debug('Ouverture porte 1...')
	Attend(5)
	Debug('Ouverture porte 2...')
	Pwrite(P22,0)
	Attend(DPORTESCAPTEURS)
	Attend(5)
	Pwrite(P12,1)
	Pwrite(P22,1)
	Debug('Portes ouvertes')
	PORTEOUV=True
	return 1
	
def FermePortes():
	global PORTEOUV
	if not PORTEOUV:
		# Les portes sont déjà fermées
		return 0
	StopMot()
	Pwrite(P21,0)
	Debug('Fermeture des portes...')
	Debug('Fermeture porte 2...')
	Attend(5)
	Pwrite(P11,0)
	Debug('Fermeture porte 1...')
	Attend(DPORTES)
	Debug('Portes fermées')
	Pwrite(P11,1)
	Pwrite(P21,1)
	PORTEOUV=False
	return 1
	
def DeplaceDome(sens):
	global POSDOME
	StopTel()
	StartMot()
	OuvrePortes()
	Debug('Demarrage moteur')
	Pwrite(MOTEUR,0)
	time.sleep(0.6)
	Pwrite(MOTEUR,1)
	Attend(DABRI)
	Attend(2)
	POSDOME=not POSDOME
	if POSDOME:
		# Abri ouvert
		StartTel()
		time.sleep(0.5)
	else:
		# Abri fermé
		FermePortes()
		StopMot()
		time.sleep(0.5)
	
def OuvreDome():
	global POSDOME
	Debug('Ouverture dome...')
	if POSDOME:
		Debug('Erreur: Abri déjà ouvert')
		return 0
	DeplaceDome(True)
	Debug('Dome ouvert')
	POSDOME=True
	return 1

def FermeDome():
	global POSDOME
	Debug('Fermeture dome...')
	if not POSDOME:
		Debug('Erreur: Abri déjà fermé')
		return 0
	DeplaceDome(False)
	FermePortes()
	Debug('Dome fermé')
	POSDOME=False
	return 1
	
##### SETUP ######
# Initialisation des entrées/sorties
# Initialisation du port série, du socket

# Sorties

Pwrite(ALIM12,1)
Pinit(ALIM12,Constants.OUTPUT)
Pwrite(ALIMTEL,1)
Pinit(ALIMTEL,Constants.OUTPUT)
Pwrite(ALIMMOT,1)
Pinit(ALIMMOT,Constants.OUTPUT)
Pwrite(MOTEUR,1)
Pinit(MOTEUR,Constants.OUTPUT)
Pwrite(P11,1)
Pinit(P11,Constants.OUTPUT)
Pwrite(P12,1)
Pinit(P12,Constants.OUTPUT)
Pwrite(P21,1)
Pinit(P21,Constants.OUTPUT)
Pwrite(P22,1)
Pinit(P22,Constants.OUTPUT)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('',1234))
s.listen(1)
s.setblocking(0)

Debug('Fin setup.')

# Etat du dome initialisation des interrupteurs
if POSDOME:
	StartTel()
	StartMot()
##### BOUCLE PRINCIPALE #####

while True:
	try:
		CMD = CmdTelnet()
		if CMD !='':
			EnvoiCommande(CMD)
			# MAJEtatPark() # Interruption ?
			# Dome bouge ?
			# Bouton arret d'urgence'
	except KeyboardInterrupt:
		raise
	time.sleep(0.5)

