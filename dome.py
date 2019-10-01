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
i2c = busio.I2C(board.SCL, board.SDA)

##### PERIPHERIQUES #####
##### CONSTANTES #####
##### MACROS #####
##### VARIABLES GLOBALES #####
CMD=''
PORTEOUV=False
POSDOME=False

# Entrées/sorties
E = {'AO': 5, 'AF': 7, 'Po1': 4, 'Po2': 0, 'Pf1': 6, 'Pf2': 2}
S = {'ALIM12': 2,'ALIMTEL': 3, 'ALIMMOT': 1, 'MOTEUR': 0, 'P11': 4, 'P12': 5, 'P21': 6, 'P22': 7}
PARK = 13
# Délais
D = {'PORTE': 40, 'PORTESCAPTEURS': 30, 'MOTEUR': 40, 'ABRI': 15}



##### FONCTIONS #####

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

def EnvoiCommande(cmd):
	global CMD
	CMD=CMD[:2]
	print(CMD)
	# Exécute la commande
	if CMD=='D+':
		OuvreDome()
	elif CMD=="D-":
		FermeDome()
	CMD=''
	global conn
	conn.close()

def Affiche(message):
	# Affiche les informations
	print(message)
	
def OuvrePortes():
	global PORTEOUV
	if PORTEOUV:
		# Les portes sont déjà ouvertes
		return True
	Affiche('Ouverture des portes...')
	Affiche('Ouverture porte 1...')
	Affiche('Ouverture porte 2...')
	Affiche ('Portes ouvertes')
	PORTEOUV=True
	
def FermePortes():
	global PORTEOUV
	if not PORTEOUV:
		# Les portes sont déjà fermées
		return True
	Affiche('Fermeture des portes...')
	Affiche('Fermeture porte 2...')
	Affiche('Fermeture porte 1...')
	Affiche('Portes fermées')
	PORTEOUV=False
	
def OuvreDome():
	global POSDOME
	Affiche('Ouverture dome...')
	if POSDOME:
		Affiche('Erreur: Abri déjà ouvert')
		return False
	OuvrePortes()
	Affiche('Dome ouvert')
	POSDOME=True

def FermeDome():
	global POSDOME
	Affiche('Fermeture dome...')
	if not POSDOME:
		Affiche('Erreur: Abri déjà fermé')
		return False
	FermePortes()
	Affiche('Dome fermé')
	POSDOME=False
	
##### SETUP ######
# Initialisation des entrées/sorties
# Initialisation du port série, du socket

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

