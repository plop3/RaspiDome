#!/usr/bin/python3
# -*- encoding: utf8 -*-



# Pilotage automatique de l'abri du télescope.
# Serge CLAUS
# GPL V3
# Version 1.0.0
# 30/09/2019
# Version python3 pour Raspberry PI


# TODO
# Remplacer POSDOME par les entrées capteurs
# Idem pour PORTEOUV
# AttendARU à faire

##### MODULES EXTERNES #####
import sys
import socket
import time
import threading
# Firmata
from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants
board = PyMata3()

##### PERIPHERIQUES #####
##### CONSTANTES #####
##### MACROS #####
##### VARIABLES GLOBALES #####
CMD=''
PORTEOUV=False
POSDOME=False


# Entrées/sorties
AO=5
AF=7
Po1=4
Po2=0
Pf1=6
Pf2=2

ALIM12=4
ALIMTEL=5
ALIMMOT=3
MOTEUR=2
P11=6
P12=7
P21=8
P22=9
PARK = 13

# Délais
DPORTES=40
DPORTESCAPTEURS=30
DMOTEUR=40
DABRI=15

PINPARK=True

##### FONCTIONS #####

def AlimStatus():
	return not board.digital_read(ALIMTEL)
def PortesOuvert():
	return (not board.digital_read(Po1) and not board.digital_read(Po2))
def PortesFerme():
	return (not board.digital_read(Pf1) and not board.digital_read(Pf2))
def AbriFerme():
	return not board.digital_read(AF)
def AbriOuvert():
	return not board.digital_read(AO)
def MoteurStatus():
	return not board.digital_read(ALIMMOT)
def StartTel():
	board.digital_write(ALIMTEL,0)
def StopTel():
	board.digital_write(ALIMTEL,1)
def StartMot():
	board.digital_write(ALIMMOT,0)
def StopMot(): 
	board.digital_write(ALIMMOT,1)
def TelPark():
	return 1

def AttendARU(delai,park,depl):
	# TODO compléter
	time.sleep(delai)
	
def FermePorte1():
	board.digital_write(P11,0)
	time.sleep(D['PORTES'])
	board.digital_write(P11,1)
	
def OuvrePorte1():
	board.digital_write(P12,0)
	time.sleep(D['PORTES'])
	board.digital_write(P12,1)
	
def CmdTelnet():
	global CMD
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(('',1234))
	s.listen(1)
	global conn
	print('****')
	while True:
		conn, addr = s.accept()
		# Lecture des données sur le port
		if CMD=='':
			CMD = conn.recv(32)
		time.sleep(1)
		
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
	elif CMD==b'P?':
		EnvoiStatus(PortesOuvert())
	elif CMD==b'D?':
		EnvoiStatus(AbriFerme())
	elif CMD==b'AU':
		EnvoiStatus('0')
		ARU()
	elif CMD==b'p-':
		FermePorte1()
	elif CMD==b'p+':
		OuvrePorte1()
	elif CMD==b'C?':
		EnvoiStatus(AbriFerme())
		EnvoiStatus(AbriOuvert())
		EnvoiStatus(PortesFerme())
		EnvoiStatus(PortesOuvert())
		EnvoiStatus(AlimStatus())
		if PINPARK:
			EnvoiMsg('p')
		else:
			EnvoiMsg('n')
		# Park
	CMD=''
	conn.close()

def Affiche(message):
	# Affiche les informations
	print(message)
	
def OuvrePortes():
	global PORTEOUV
	if PORTEOUV:
		# Les portes sont déjà ouvertes
		return 0
	StartMot()
	Affiche('Ouverture des portes...')
	board.digital_write(P12,0)
	Affiche('Ouverture porte 1...')
	AttendARU(5,False,False)
	Affiche('Ouverture porte 2...')
	board.digital_write(P22,0)
	AttendARU(D['PORTESCAPTEURS'],False,False)
	#while not PortesOuvert():
	#	AttendARU(0.1,False,False)
	AttendARU(5,False,False)
	board.digital_write(P12,1)
	board.digital_write(P22,1)
	Affiche ('Portes ouvertes')
	PORTEOUV=True
	return 1
	
def FermePortes():
	global PORTEOUV
	if not PORTEOUV:
		# Les portes sont déjà fermées
		return 0
	StopMot()
	P21.value=False
	board.digital_write(P21,0)
	Affiche('Fermeture des portes...')
	Affiche('Fermeture porte 2...')
	AttendARU(5,False,False)
	board.digital_write(P11,0)
	Affiche('Fermeture porte 1...')
	AttendARU(D['PORTES'],False,False)
	Affiche('Portes fermées')
	board.digital_write(P11,1)
	board.digital_write(P21,1)
	PORTEOUV=False
	return 1
	
def DeplaceDome(sens):
	if not PINPARK:
		Affiche("Erreur: télescope non parqué")
		return False
	StopTel()
	if not PortesOuvert:
		if not MoteurStatus():
			StartMot()
		OuvrePortes()
	elif not MoteurStatus():
		StartMot()
		AttendARU(MOTEUR,True, False)
	board.digital_write(MOTEUR,0)
	time.sleep(0.6)
	board.digital_write(MOTEUR,1)
	AttendARU(ABRI,True, False)
	# TODO Supprimer les commentaires ci-dessous
	##while (not AbriOuvert() and not AbriFerme())
	##	AttendARU(1,True, False)
	AttendARU(2, True , False)
	# TODO Commuter les lignes suivantes (test sans capteurs)
	POSDOME= not POSDOME
	# POSDOME = not AbriOuvert()
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
	Affiche('Ouverture dome...')
	if POSDOME:
		Affiche('Erreur: Abri déjà ouvert')
		return False
	DeplaceDome(True)
	Affiche('Dome ouvert')
	POSDOME=True
	return 1

def FermeDome():
	global POSDOME
	Affiche('Fermeture dome...')
	if not POSDOME:
		Affiche('Erreur: Abri déjà fermé')
		return False
	DeplaceDome(False)
	FermePortes()
	Affiche('Dome fermé')
	POSDOME=False
	return 1
	
##### SETUP ######
# Initialisation des entrées/sorties
# Initialisation du port série, du socket

# Entrées
board.set_pin_mode(AO,Constants.PULLUP)
board.set_pin_mode(AF,Constants.PULLUP)
board.set_pin_mode(Po1,Constants.PULLUP)
board.set_pin_mode(Po2,Constants.PULLUP)
board.set_pin_mode(Pf1,Constants.PULLUP)
board.set_pin_mode(Pf2,Constants.PULLUP)

# Sorties
board.set_pin_mode(ALIM12,Constants.OUTPUT)
board.digital_write(ALIM12,1)
board.set_pin_mode(ALIMMOT,Constants.OUTPUT)
board.digital_write(ALIMMOT,1)
board.set_pin_mode(MOTEUR,Constants.OUTPUT)
board.digital_write(MOTEUR,1)
board.set_pin_mode(P11,Constants.OUTPUT)
board.digital_write(P11,1)
board.set_pin_made(P12,Constants.OUTPUT)
board.digital_write(P12,1)
board.set_pin_mode(P21,Constants.OUTPUT)
board.digital_write(P21,1)
board.set_pin_mode(P22,Constants.OUTPUT)
board.digital_write(P22,1)

# Etat du dome initialisation des interrupteurs
if AbriOuvert():
	StartTel()
	StartMot()
##### BOUCLE PRINCIPALE #####
tkb = threading.Thread(target=CmdTelnet)
tkb.start()
time.sleep(2)

while True:
	try:
		if CMD !='':
			EnvoiCommande(CMD)
			# MAJEtatPark() # Interruption ?
			# Dome bouge ?
			# Bouton arret d'urgence'
			time.sleep(1)
	except KeyboardInterrupt:
		raise

