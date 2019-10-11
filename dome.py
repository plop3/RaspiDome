#!/usr/bin/python3
# -*- encoding: utf8 -*-


# Pilotage automatique de l'abri du télescope.
# Serge CLAUS
# GPL V3
# Version 1.0.0
# 30/09/2019
# Version python3 pour Raspberry PI

##### MODULES EXTERNES #####
import sys
import socket
import time
import threading
from rpi_TM1638 import TMBoards

# TM1638
DIO=19
CLK=13
STB=6

TM=TMBoards(DIO, CLK, STB, 0)

CMD=''
SERIAL="/dev/MySensors"
FIRMATA="/dev/Firmata"

# Firmata
from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants
board = PyMata3(com_port=FIRMATA)

# Entrées/sorties
AO=17	#A1
AF=16	#A0
Po1=18	#A2
Po2=19	#A3
Pf1=20	#A4
Pf2=21	#A5

PARK = 22	#A6

MOTEUR=11	#D11
ALIMMOT=10	#D10
ALIM12=9	#D9
ALIMTEL=8	#D8
P11=7		#D7
P12=6		#D6
P21=5		#D5
P22=4		#D4

# Délais
DPORTES=40
DPORTESCAPTEURS=30
DMOTEUR=40
DABRI=22

##### CLASSES #####
class ARUExcept(Exception):
	pass
	
##### FONCTIONS #####
def PStatus(pin):
	if pin<16:
		return board.get_pin_state(pin)[2]
	elif pin > 21:
		if board.analog_read(pin-16)> 300:
			return True
		else:
			return False
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
def PortesOuvert():
	return not PStatus(Po1) and not PStatus(Po2)
def PorteFerme():
	return not PStatus(Pf1)	# Pas de capteur sur la porte 2 pour l'instant
def AbriOuvert():
	return not PStatus(AO)
def AbriFerme():
	return not PStatus(AF)
def TelPark():
	return PStatus(PARK)

def ARU(msg):
	# On coupe tout
	Pwrite(ALIMMOT,1)
	Pwrite(ALIMTEL,1)
	Pwrite(ALIM12,1)
	Prite(Po1,1)
	Prite(Po2,1)
	Prite(Pf1,1)
	Prite(Pf2,1)
	# On prévient du problème
	Debug('ARU '+msg)
	# On leve l'exception ARUExcept
	raise ARUExcept
	
def delai():
	pass
def Attend(delai,park,depl,porte):
	t=threading.Timer(delai)
	t.start()
	nbpark=0
	nbpos=0
	nbporte=0
	errmax=2
	while t.is_alive():
		# Surveillance du déplacement
		if park:
			if not TelPark():
				nbpark+=1
			else: 
				nbpark=0
			if nbpark > errmax:
				ARU('Erreur Park')
		if depl:
			if not AbriFerme() and not AbriOuvert():
				nbpos+=1
			else:
				nbpos=0
			if nbpos > errmax:	
				ARU('Erreur position abri')
		if porte:
			if not PortesOuvert():
				nbporte+=1
			else:
				nbporte=0
			if nbporte > errmax:
				ARU('Erreur portes')
		# Verification d'une commande ARU (AU#)
		CMD = LireCMD()
		if CMD =='AU':
			ARU("Demande arret d'urgence")
		time.sleep(0.1)
		
def FermePorte1():
	Pwrite(P11,0)
	time.sleep(DPORTES)
	Pwrite(P11,1)
	
def OuvrePorte1():
	Pwrite(P12,0)
	time.sleep(DPORTES)
	Pwrite(P12,1)
def OuvrePorte2():
	Pwrite(P22,0)
	time.sleep(DPORTES)
	Pwrite(P22,1)

def CmdTelnet():
	global conn
	try:
		conn, addr = s.accept()
		CMD = conn.recv(32)
	except BlockingIOError:
		return ''
	else:
		return CMD
def CmdSerial():
	pass
def CmdButtons():
	pass
def LireCMD():
	CMD=CmdSerial()
	if not CMD:
		# Lecture du port réseau
		CMD=CmdTelnet()
		if not CMD:
			# Lecture du/des clavier(s)
			CMD=CmdButtons()
	return CMD

def EnvoiStatus(ret):
	conn.sendall(str(int(ret)).encode('utf8'))
def EnvoiMsg(ret):
	conn.sendall(str(ret).encode('utf8'))
	
def EnvoiCommande(cmd,mode):	# cmd: commande reçue, mode: 1: auto, 0: manuel
	global CMD
	global conn
	CMD=CMD[:2]
	print(CMD)
	# Exécute la commande
	if mode:
		if CMD==b'D+':
			EnvoiStatus(OuvreDome())
		elif CMD==b"D-":
			EnvoiStatus(FermeDome())
		elif CMD==b'p-':
			FermePorte1()
		elif CMD==b'p+':
			OuvrePorte1()
		elif CMD==b'P+':
			EnvoiStatus(OuvrePortes())
		elif CMD==b'P-':
			EnvoiStatus(FermePortes())
		elif CMD==b'A+':
			StartTel()
			EnvoiStatus(AlimStatus())
		elif CMD==b'A-':
			StopTel()
			EnvoiStatus(AlimStatus())
		elif CMD==b'A?':
			EnvoiStatus(AlimStatus())
		elif CMD==b'P?':
			EnvoiStatus(PortesOuvert())
		elif CMD==b'D?':
			EnvoiStatus(AbriOuvert())
		elif CMD==b'C?':
			EnvoiStatus(AbriOuvert())
			EnvoiStatus(AbriFerme())
			EnvoiStatus(PortesOuvert())
			EnvoiStatus(PortesFerme())
			EnvoiStatus(AlimStatus())
			if TelPark():
				EnvoiStatus('p')
			else:
				EnvoiStatus('n')
	else:
		if CMD==b'mp':
			# Ouvre les portes
			OuvrePorte1()
			OuvrePorte2()
		elif CMD==b'md':
			# Deplace le dome
			DeplaceDomeManuel()
		elif CMD==b'OK':
			# Passage en mode auto
			mode=1
	return mode
	conn.close()

def Debug(message):
	# Affiche les informations
	print(message)
	
def OuvrePortes():
	if PortesOuvert():
		# Les portes sont déjà ouvertes
		return 0
	if not AbriFerme() and not AbriOuvert():
		# Abri non fermé, fermeture des portes impossible
		Debug("Fermeture des portes impossible: Position incorrecte de l'abri.")
		return 0
	StartMot()
	Debug('Ouverture des portes...')
	Pwrite(P12,0)
	Debug('Ouverture porte 1...')
	Attend(5,1,1,0)
	Debug('Ouverture porte 2...')
	Pwrite(P22,0)
	Attend(DPORTESCAPTEURS,1,1,0)
	while not PortesOuvert():
		Attend(0.1,1,1,0)
	Attend(5,1,1,0)
	Pwrite(P12,1)
	Pwrite(P22,1)
	Debug('Portes ouvertes')
	return 1
	
def FermePortes():
	if not PortesOuvert():
		Debug('Portes déjà fermées')
		# Les portes sont déjà fermées
		return 0
	if not AbriFerme():
		# Abri non fermé, fermeture des portes impossible
		Debug('Fermeture des portes impossible: Abri non fermé. ')
		return 0
	# TODO Voir si utile de vérifier l'état Park
	StopMot()
	Pwrite(P21,0)
	Debug('Fermeture des portes...')
	Debug('Fermeture porte 2...')
	Attend(5,1,1,0)
	Pwrite(P11,0)
	Debug('Fermeture porte 1...')
	Attend(DPORTES,1,1,0)
	Debug('Portes fermées')
	Pwrite(P11,1)
	Pwrite(P21,1)
	if PortesOuvert():
		# Problème de fermeture des portes
		Debug("Problème de fermeture des portes")
		return 0
	return 1

def DeplaceDomeManuel():
	StopTel()
	StartMot()
	Attend(DMOTEUR,False, False,False)
	Pwrite(MOTEUR,0)
	time.sleep(0.6)
	Pwrite(MOTEUR,1)
	Attend(DABRI,1,0,1)
	
def DeplaceDome(sens):	# 0: Ferme le dome, 1: Ouvre le dome
	EtatAbri=AbriFerme()	# Enregistre la position actuelle de l'abri
	if (not AbriFerme() and not AbriOuvert()) or (AbriFerme() and AbriOuvert()):
		# Problème de capteur
		ARU('Problème de capteur de position abri')
		return 0
	if not TelPark():
		# Télescope non parqué
		# TODO Tenter de parquer le télescope
		Debug('Télescope non parqué')
		return 0
	StopTel()
	if not PortesOuvert:
		if not MoteurStatus():
			StartMot()
		OuvrePortes()
	elif not MoteurStatus():
		StartMot()
		Attend(DMOTEUR,True, False,False)
	#OuvrePortes()
	Debug('Demarrage moteur')
	Pwrite(MOTEUR,0)
	time.sleep(0.6)
	Pwrite(MOTEUR,1)
	Attend(DABRI,1,0,1)
	while (not AbriOuvert() and not AbriFerme()):
		Attend(1,True, False, True)
	if EtatAbri==AbriOuvert():
		Debug("L'abri ne s'est pas déplacé")
		return 0
	elif AbriOuvert() or AbriFerme():
		return 1
	else:
		Debug("Position incorrecte de l'abri")
		# Abri ni ouvert, ni fermé :-(
		ARU("Erreur de position abri")
		return 0
			
def OuvreDome():
	Debug('Ouverture dome...')
	if AbriOuvert():
		Debug('Erreur: Abri déjà ouvert')
		return 0
	StartTel()
	if DeplaceDome(True):
		Debug('Dome ouvert')
		return 1
	else:
		Debug("Problème déplacement dome")
		StopTel()
		return 0

def FermeDome():
	Debug('Fermeture dome...')
	if AbriFerme():
		Debug('Erreur: Abri déjà fermé')
		return 0
	if DeplaceDome(False):
		StopMot()
		FermePortes()
		StopTel()
		Debug('Dome fermé')
		return 1
	else:
		Debug("Problème déplacement dome")
		return 0
	
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

# Entrées 
Pinit(A0,Constants.PULLUP)
Pinit(AF,Constants.PULLUP)
Pinit(Po1,Constants.PULLUP)
Pinit(Po2,Constants.PULLUP)
Pinit(Pf1,Constants.PULLUP)
Pinit(Pf2,Constants.PULLUP)
Pinit(PARK-16,Constants.ANALOG)

TM.clearDisplay()
#TM.segments[0]="START   "

# Socket de communication réseau
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('',1234))
s.listen(1)
s.setblocking(0)

Debug('Fin setup.')
TM.segments[0]="On      "
TM.leds[0]=1

# Etat du dome initialisation des interrupteurs
if AbriOuvert():
	StartTel()
	StartMot()
##### BOUCLE PRINCIPALE #####
mode=1		# 1: mode auto, 0: mode manuel
while True:
	try:
		CMD = LireCMD()
		if CMD !='':
			mode=EnvoiCommande(CMD,mode)
			# MAJEtatPark() # Interruption ?
			# Dome bouge ?
			if not AbriOuvert() and not AbriFerme():
				ARU("Erreur de position Abri")
			# TODO Bouton arret d'urgence
	except KeyboardInterrupt:
		raise
	except ARUExcept:
		# Arret d'urgence
		mode=0	# Passage en mode manuel
	time.sleep(0.5)

