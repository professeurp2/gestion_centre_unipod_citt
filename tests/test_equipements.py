from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.equipements.models import Equipement, Habilitation, Incident, Maintenance, Reservation

from . import fabriques as F


class ReservationTests(TestCase):
    def setUp(self):
        self.usager = F.usager()
        self.machine = F.equipement()

    def reserver(self, **kw):
        debut, fin = kw.pop("creneau", F.creneau())
        r = Reservation(equipement=kw.pop("equipement", self.machine), usager=kw.pop("usager", self.usager),
                        debut=debut, fin=fin, **kw)
        r.full_clean()
        r.save()
        return r

    def test_reservation_valide(self):
        r = self.reserver()
        self.assertEqual(r.duree_heures, 2)

    def test_chevauchement_refuse(self):
        self.reserver(creneau=F.creneau(heure=9, heures=2))
        with self.assertRaisesMessage(ValidationError, "chevauche"):
            self.reserver(creneau=F.creneau(heure=10, heures=2))

    def test_creneau_adjacent_et_reservation_annulee_acceptes(self):
        self.reserver(creneau=F.creneau(heure=9, heures=2))
        self.reserver(creneau=F.creneau(heure=11, heures=1))
        self.reserver(creneau=F.creneau(jours=2), statut="annulee")
        self.reserver(creneau=F.creneau(jours=2))

    def test_fin_avant_debut(self):
        debut, fin = F.creneau()
        with self.assertRaises(ValidationError):
            self.reserver(creneau=(fin, debut))

    def test_machine_en_panne_non_reservable(self):
        self.machine.etat = Equipement.Etat.PANNE
        self.machine.save()
        with self.assertRaisesMessage(ValidationError, "indisponible"):
            self.reserver()

    def test_habilitation_requise(self):
        machine = F.equipement(habilitation=True)
        with self.assertRaisesMessage(ValidationError, "habilitation"):
            self.reserver(equipement=machine)
        hab = Habilitation.objects.create(usager=self.usager, categorie=machine.categorie,
                                          date_expiration=timezone.localdate() - timedelta(days=1))
        with self.assertRaisesMessage(ValidationError, "habilitation"):
            self.reserver(equipement=machine)
        hab.date_expiration = None
        hab.save()
        self.reserver(equipement=machine)


class MaintenanceIncidentTests(TestCase):
    def test_incident_majeur_met_la_machine_en_panne(self):
        machine = F.equipement()
        Incident.objects.create(equipement=machine, gravite="mineure", description="Rayure")
        machine.refresh_from_db()
        self.assertEqual(machine.etat, Equipement.Etat.OPERATIONNEL)
        Incident.objects.create(equipement=machine, gravite="majeure", description="Moteur HS")
        machine.refresh_from_db()
        self.assertEqual(machine.etat, Equipement.Etat.PANNE)

    def test_prochaine_maintenance(self):
        machine = F.equipement(periodicite_maintenance=30, date_acquisition=date(2026, 1, 1))
        self.assertEqual(machine.prochaine_maintenance, date(2026, 1, 31))
        Maintenance.objects.create(equipement=machine, type="preventive", statut="terminee",
                                   date_planifiee=date(2026, 3, 1), date_realisation=date(2026, 3, 2),
                                   description="RAS")
        self.assertEqual(machine.prochaine_maintenance, date(2026, 4, 1))

    def test_maintenance_terminee_exige_une_date(self):
        m = Maintenance(equipement=F.equipement(), type="corrective", statut="terminee",
                        date_planifiee=date(2026, 1, 1), description="x")
        with self.assertRaises(ValidationError):
            m.full_clean()
