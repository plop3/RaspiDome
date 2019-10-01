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

import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017
from digitalio import Direction, Pull
i2c = busio.I2C(board.SCL, board.SDA)
mcp = MCP23017(i2c,0x24)

##### PERIPHERIQUES #####
##### CONSTANTES #####
##### MACROS #####
##### VARIABLES GLOBALES #####
CMD=''
PORTEOUV=False
POSDOME=False


# Entrées/sorties
#E = {'AO': 5, 'AF': 7, 'Po1': 4, 'Po2': 0, 'Pf1': 6, 'Pf2': 2}
E = {'AO': 13, 'AF': 15, 'Po1': 12, 'Po2': 8, 'Pf1': 14, 'Pf2': 10}
S = {'ALIM12': 2,'ALIMTEL': 3, 'ALIMMOT': 1, 'MOTEUR': 0, 'P11': 4, 'P12': 5, 'P21': 6, 'P22': 7}
PARK = 13
# Délais
D = {'PORTES': 40, 'PORTESCAPTEURS': 30, 'MOTEUR': 40, 'ABRI': 15}

PINPARK=True

##### FONCTIONS #####

def AlimStatus():
	return not ALIMTEL.value
def PortesOuvert():
	return (not Po1.value and not Po2.value)
def PortesFerme():
	return (not Pf1.value and not Pf2.value)
def AbriFerme():
	return not AF.value
def AbriOuvert():
	return not AO.value
def MoteurStatus():
	return not ALIMMOT.value
def StartTel():
	ALIMTEL.value=False
def StopTel():
	ALIMTEL.value=True
def StartMot():
	ALIMMOT.value=False
def StopMot(): 
	ALIMMOT.value=True
def TelPark():
	return 1

def AttendARU(delai,park,depl):
	time.sleep(delai)
	
def FermePorte1():
	P11.value=False
	time.sleep(D['PORTES'])
	P11.value=True
	
def OuvrePorte1():
	P12.value=False
	time.sleep(D['PORTES'])
	P12.value=True
	
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
	P12.value=False
	Affiche('Ouverture porte 1...')
	AttendARU(5,False,False)
	Affiche('Ouverture porte 2...')
	P22.value=False
	AttendARU(D['PORTESCAPTEURS'],False,False)
	#while not PortesOuvert():
	#	AttendARU(0.1,False,False)
	AttendARU(5,False,False)
	P12.value=True
	P22.value=True
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
	Affiche('Fermeture des portes...')
	Affiche('Fermeture porte 2...')
	AttendARU(5,False,False)
	P11.value=False
	Affiche('Fermeture porte 1...')
	AttendARU(D['PORTES'],False,False)
	Affiche('Portes fermées')
	P11.value=True
	P21.value=True
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
	else if not MoteurStatus():
		StartMot()
		AttendARU(MOTEUR,True, False)
	MOTEUR.value=False	
	time.sleep(0.6)
	MOTEUR.value=True
	# TODO Continuer ici
	
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
AO=mcp.get_pin(E['AO'])
AO.direction=Direction.INPUT
AO.pull=Pull.UP
AF=mcp.get_pin(E['AF'])
AF.direction=Direction.INPUT
AF.pull=Pull.UP
Po1=mcp.get_pin(E['Po1'])
Po1.direction=Direction.INPUT
Po1.pull=Pull.UP
Po2=mcp.get_pin(E['Po2'])
Po2.direction=Direction.INPUT
Po2.pull=Pull.UP
Pf1=mcp.get_pin(E['Pf1'])
Pf1.direction=Direction.INPUT
Pf1.pull=Pull.UP
Pf2=mcp.get_pin(E['Pf2'])
Pf2.direction=Direction.INPUT
Pf2.pull=Pull.UP

# Sorties
#S = {'ALIM12': 2,'ALIMTEL': 3, 'ALIMMOT': 1, 'MOTEUR': 0, 'P11': 4, 'P12': 5, 'P21': 6, 'P22': 7}
ALIM12=mcp.get_pin(S['ALIM12'])
ALIM12.direction=Direction.OUTPUT
ALIM12.value=True
ALIMTEL=mcp.get_pin(S['ALIM12'])
ALIMTEL.direction=Direction.OUTPUT
ALIMTEL.value=True
ALIMMOT=mcp.get_pin(S['ALIMMOT'])
ALIMMOT.direction=Direction.OUTPUT
ALIMMOT.value=True
MOTEUR=mcp.get_pin(S['MOTEUR'])
MOTEUR.direction=Direction.OUTPUT
MOTEUR.value=True
P11=mcp.get_pin(S['P11'])
P11.direction=Direction.OUTPUT
P11.value=True
P12=mcp.get_pin(S['P12'])
P12.direction=Direction.OUTPUT
P12.value=True
P21=mcp.get_pin(S['P21'])
P21.direction=Direction.OUTPUT
P21.value=True
P22=mcp.get_pin(S['P22'])
P22.direction=Direction.OUTPUT
P22.value=True


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

