from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.personnel.models import Conge
from apps.programmes.models import Inscription, JalonProjet, Programme, Projet, Session

from . import fabriques as F


class CongeTests(TestCase):
    def test_approbation_decompte_le_solde(self):
        agent = F.personnel(solde_conges=20)
        user = get_user_model().objects.create_user("rh", password="x")
        conge = Conge.objects.create(personnel=agent, date_debut=date(2026, 5, 4), date_fin=date(2026, 5, 8))
        conge.approuver(user)
        agent.refresh_from_db()
        self.assertEqual(agent.solde_conges, 15)
        self.assertEqual(conge.statut, Conge.Statut.APPROUVE)
        with self.assertRaises(ValidationError):
            conge.approuver(user)

    def test_conge_maladie_ne_decompte_pas(self):
        agent = F.personnel(solde_conges=20)
        conge = Conge.objects.create(personnel=agent, type="maladie", date_debut=date(2026, 5, 4),
                                     date_fin=date(2026, 5, 5))
        conge.approuver(None)
        agent.refresh_from_db()
        self.assertEqual(agent.solde_conges, 20)


class ProgrammeTests(TestCase):
    def setUp(self):
        self.centre = F.centre()
        self.programme = Programme.objects.create(centre=self.centre, titre="Bootcamp", type="bootcamp",
                                                  date_debut=date(2026, 1, 1))

    def test_session_complete(self):
        debut = timezone.now()
        session = Session.objects.create(programme=self.programme, titre="S1", debut=debut,
                                         fin=debut + timedelta(hours=2), capacite=1)
        Inscription.objects.create(session=session, usager=F.usager(self.centre))
        with self.assertRaisesMessage(ValidationError, "complète"):
            Inscription(session=session, usager=F.usager(self.centre)).full_clean()

    def test_jalon_fait_progresser_le_stade(self):
        projet = Projet.objects.create(centre=self.centre, titre="P", porteur=F.usager(self.centre))
        JalonProjet.objects.create(projet=projet, titre="Premier prototype", stade_atteint="prototype")
        projet.refresh_from_db()
        self.assertEqual(projet.stade, Projet.Stade.PROTOTYPE)


class RolesTests(TestCase):
    def test_init_unipod_idempotent_et_roles(self):
        call_command("init_unipod", stdout=open("/dev/null", "w"))
        call_command("init_unipod", stdout=open("/dev/null", "w"))
        self.assertTrue(Group.objects.filter(name="Magasin").exists())
        user = get_user_model().objects.create_user("mag", password="x", role="magasin")
        self.assertTrue(user.is_staff)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Magasin"])
        self.assertTrue(user.has_perm("stocks.add_mouvementstock"))
        self.assertFalse(user.has_perm("personnel.change_personnel"))
        user.role = "rh"
        user.save()
        user = get_user_model().objects.get(pk=user.pk)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Ressources humaines"])
        self.assertTrue(user.has_perm("personnel.change_personnel"))
