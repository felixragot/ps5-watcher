# PS5 Watcher

Surveille la disponibilité de la PlayStation 5 Édition numérique (modèle Slim) sur la page officielle PlayStation France et envoie une alerte Telegram.

Le programme ne se connecte à aucun compte et ne réalise aucun achat.

## Fonctionnement

- Une vérification toutes les 5 minutes via GitHub Actions.
- Statut calculé à partir du JSON-LD `availability`, du `type` GameCTA du SKU cible et du texte visible.
- Un message au passage vers disponible ou inconnu.
- Un rappel toutes les 30 minutes seulement tant que le produit reste disponible.
- Aucun message tant que le produit reste indisponible.
- L'état est conservé dans `state.json` sur la branche principale.

## Créer le bot Telegram

1. Ouvrir Telegram et contacter `@BotFather`.
2. Envoyer `/newbot`.
3. Donner un nom puis un identifiant se terminant par `bot`.
4. Copier le token reçu. Ne jamais le mettre dans le dépôt.
5. Envoyer un message à votre nouveau bot.
6. Ouvrir cette URL dans le navigateur avec votre token :

   `https://api.telegram.org/bot<VOTRE_TOKEN>/getUpdates`

7. Dans la réponse JSON, relever la valeur numérique `message.chat.id`.

🧑 **Action utilisateur** : conserver le token et le chat ID pour les secrets GitHub.

## Installation locale

Python 3.14 est requis.

```powershell
py -m pip install -r requirements.txt
copy .env.example .env
py main.py --dry-run --jitter 0
py -m unittest discover -s tests -v
```

Sous PowerShell, renseigner ensuite les variables :

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="..."
py main.py --dry-run --jitter 0
py main.py --force-notify --dry-run --jitter 0
```

`--force-notify --dry-run` simule l'envoi sans réseau Telegram. Pour un vrai test Telegram :

```powershell
py main.py --force-notify --jitter 0
```

## Mise en ligne

1. Créer un dépôt public GitHub.
2. Pousser ce projet.
3. Dans **Settings → Secrets and variables → Actions**, créer :
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Dans **Settings → Actions → General**, autoriser `Read and write permissions` pour que `state.json` puisse être sauvegardé.
5. Lancer le workflow manuellement depuis l'onglet **Actions**.

Le workflow est prévu avec un schedule décalé pour limiter les collisions avec les autres exécutions GitHub.

GitHub peut désactiver les workflows planifiés après 60 jours d'inactivité sur un dépôt public. Aller dans **Actions**, ouvrir le workflow puis le réactiver si nécessaire.

## Ajout d'un produit

Ajouter une entrée dans `config/products.json` :

```json
{
  "name": "Nom du produit",
  "url": "https://www.playstation.com/fr-fr/...",
  "sku": "SKU-CIBLE"
}
```

Le code ne nécessite aucune modification.

## Choix de persistance

L'état est commité dans `state.json` sur la branche principale. C'est plus fiable qu'un cache Actions : le fichier est conservé explicitement entre les exécutions et reste inspectable dans le dépôt. Comme le dépôt est public, `state.json` ne contient que des statuts et dates de notification, sans secret.

## Sécurité

- Ne jamais écrire le token dans `.env.example`, le code, les tests ou les logs.
- `.env` est ignoré par Git.
- Si le token fuit : `/revoke` dans `@BotFather`, puis créer un nouveau bot ou token.
