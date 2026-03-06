"""
Generate INSERT + UPDATE SQL for the 38 sites missing short_url.
Run locally: python scripts/gen_backfill_sql.py > /tmp/backfill.sql
"""
import re, secrets, string, uuid
from datetime import datetime

LOWER_ALPHA = string.ascii_lowercase
LOWER_ALPHANUM = string.ascii_lowercase + string.digits
SITE_BASE = "https://sites.lavish.solutions"
SHORTENER = "https://lvsh.cc"


def gen_slug(name):
    letters = re.sub(r"[^a-zA-Z]", "", name).lower()[:4]
    while len(letters) < 4:
        letters += secrets.choice(LOWER_ALPHA)
    suffix = "".join(secrets.choice(LOWER_ALPHANUM) for _ in range(3))
    return letters + suffix


SITES = [
    ("1f52f2ed-ac69-424d-a6f0-75e9b3a29b7c", "redwood-plumbing-service-repair-llc-1770177583706-701a227f", "701a227f-577e-467b-a545-5c0e2fd31650", "Redwood Plumbing Service Repair LLC"),
    ("9cb21a75-c2c7-4b8c-a187-1d519ae7698b", "nathaniel-flatt-licensed-marriage-family-therapist-1771189088836-fe571459", "fe571459-6b71-4b0a-9857-5d79fcee2b52", "Nathaniel Flatt Licensed Marriage Family Therapist"),
    ("5be95dca-75c3-44e3-9c0c-54c0ad8e7c77", "walker-plumbing-heating-1770184670466-1dd289fa", "1dd289fa-5a32-448f-a9e4-b7bee7706a9e", "Walker Plumbing Heating"),
    ("d1989cce-6259-4d45-b265-4f48a1193d86", "miguel-perez-painting-corp-1771178087240-e6200d0e", "e6200d0e-05dc-4061-8952-7d8a7a16e607", "Miguel Perez Painting Corp"),
    ("053636a6-ad83-44bc-8199-734bdabc687c", "west-la-paint-more-1771178060072-ad5b8f04", "ad5b8f04-5abf-4c2e-98b7-4876470fd8bf", "West LA Paint More"),
    ("24555381-8634-40cb-bfdd-f319b01c947c", "los-angeles-general-painting-1771178169616-22bffdf4", "22bffdf4-e563-4126-a814-e76d0d8beb48", "Los Angeles General Painting"),
    ("99fe592c-e6f9-426c-a903-08b519b1682b", "mister-sewer-plumbing-hvac-1770177582282-4e00a261", "4e00a261-d142-4099-b6e8-cf0edea18f61", "Mister Sewer Plumbing HVAC"),
    ("51fee957-46bf-42ee-bb9d-d11eec93e521", "trees-counseling-1771189247080-c15ea1bf", "c15ea1bf-e2db-483e-84fb-ebbf0f2d5ff2", "Trees Counseling"),
    ("c5377b0f-6829-4509-8ec7-8e71f8810d82", "24-7-plumber-mr-rooter-1770270514513-c3d4e024", "c3d4e024-4430-4a5b-ab20-39daec56ff41", "Plumber Mr Rooter"),
    ("33ee0099-14db-426f-96ee-5138ce0f6d71", "global-first-accounting-group-1771101103613-c486b073", "c486b073-105b-4a48-ab73-7b3d978efc7c", "Global First Accounting Group"),
    ("63af7c40-acd7-4599-aaf1-57c995cd22bc", "kenneth-k-suh-cpa-1771101143027-6a9ed52e", "6a9ed52e-1274-4ed4-8e51-610b9455d2de", "Kenneth K Suh CPA"),
    ("7e332863-9ea3-4e76-8d3c-4ae7872db6c2", "a-m-plumbing-repair-llc-1770270963028-d0530b7d", "d0530b7d-c4b9-462a-96a4-c911859f914f", "AM Plumbing Repair LLC"),
    ("33c1035d-308e-4637-ac0e-76b62a7fc983", "body-care-chiropractic-1771191619232-ea4f3da7", "ea4f3da7-238e-4645-ac21-2a4fd8725c54", "Body Care Chiropractic"),
    ("e37a5717-fd1f-40e9-bc21-9a33049e8acc", "thriving-center-of-psychology-1771188963689-ad3a6003", "ad3a6003-0615-406d-b17d-ecd85d5ceed3", "Thriving Center of Psychology"),
    ("e827d23f-8d39-4b95-a960-d9564f88a8e7", "puget-seattle-plumbers-and-drain-cleaning-co-1770274800750-accdfdd4", "accdfdd4-4076-498b-9962-81438130fbe1", "Puget Seattle Plumbers"),
    ("3f4aed24-1108-44ca-801e-c1b5b9d378a0", "ar-plumbing-solutions-llc-1770182566495-d9ec17d5", "d9ec17d5-1c5a-4aa7-a551-3bb99d413f25", "AR Plumbing Solutions LLC"),
    ("2a31cf1f-ef0b-4b92-b90f-675d973b97eb", "sparks-plumbing-and-drain-cleaning-1770177586240-fa20b0c6", "fa20b0c6-4268-41b1-8850-ccfa4d3b9f47", "Sparks Plumbing"),
    ("9d067e22-fb92-456e-8541-8408f9eea0c7", "r-d-eikey-plumbing-llc-1770275626481-2652dd7a", "2652dd7a-a3a1-4464-bec4-2d62bdeecd1e", "RD Eikey Plumbing LLC"),
    ("f5f457ea-f682-4cbd-912b-544cf584fb50", "nyc-plumbing-heating-drain-cleaning-1770270516683-fe955ad3", "fe955ad3-9e62-4e1c-9670-509423a0cf9f", "NYC Plumbing Heating"),
    ("c6c94867-d619-4141-b180-ae8ddb8b5d92", "hamilton-plumbing-heating-air-conditioning-1770275632180-92a3b527", "92a3b527-20dd-4bbf-9150-d466d638d96f", "Hamilton Plumbing Heating"),
    ("37450b46-c41b-4f9c-9013-c1b40a0d0fcd", "nix-plumbing-1770275625297-fa35cfad", "fa35cfad-07fe-4762-bab4-94ee448e0af6", "Nix Plumbing"),
    ("a69ebe29-ead0-4e04-a1ad-fd3ed91df63e", "lee-s-plumbing-1770182566360-dcfac76d", "dcfac76d-68af-4312-9b41-dd35db3690c7", "Lees Plumbing"),
    ("a8e05fbe-b1e0-4b09-a91c-458e9d547ddd", "camp-clinic-los-angeles-1771107143680-bf7e6d04", "bf7e6d04-b14b-416c-8f32-a099f49e95aa", "CAMP Clinic Los Angeles"),
    ("9e374624-2d2d-41c6-b21a-36b2e95c7b4d", "holiday-humane-society-clinic-1771117933188-12629d91", "12629d91-7ceb-411a-9c62-7163e17752b1", "Holiday Humane Society Clinic"),
    ("ed7ba631-7ca3-45db-b5aa-09a493bc3385", "jeongtherapy-group-anxiety-trauma-1771189005460-3c8c75b3", "3c8c75b3-ca6c-40cf-bd9f-f199afd3517f", "JeongTherapy Group"),
    ("7b2fb29f-3cb2-47f2-b4f4-83b460fd41c8", "louisiana-hydro-blast-solutions-llc-1770183670623-76902318", "76902318-5475-423f-aaa8-3ed4b4fcdc52", "Louisiana Hydro Blast Solutions"),
    ("3c2fad51-4ccf-43bb-bc04-66f93ce896a9", "the-melrose-vet-1771129851869-80f1af2f", "80f1af2f-dfe8-40f5-93b9-99acb082bb28", "The Melrose Vet"),
    ("2b854f42-8d71-4008-b892-c6f65fbc2530", "beetz-jos-h-plumbing-co-inc-1770183669535-362efff0", "362efff0-5952-4f34-8ae5-79a3487321b5", "Beetz Plumbing Co"),
    ("bcf305bd-d967-45c1-8c14-d44c377585cd", "plumbing-contractors-llc-1770271693362-130a7992", "130a7992-4e23-434c-9258-e5160dcc9a08", "Plumbing Contractors LLC"),
    ("99fc7786-33ce-4fb3-940b-d876e433488f", "apple-plumbing-llc-1770184431571-2d98d1a8", "2d98d1a8-4c7f-4015-99be-c57c938a88e1", "Apple Plumbing LLC"),
    ("5a1234f0-1816-4d6b-ba0d-eb269901c7ab", "penascino-plumbing-and-heating-inc-1770275627611-2b73d830", "2b73d830-b68a-4e6d-badc-cdea7f89dec7", "PENASCINO Plumbing Heating"),
    ("fabc983c-c05e-4aa8-8a29-8b62a8fe559a", "goin-plumbing-1770275370793-fc96e5c6", "fc96e5c6-37a2-4304-8b32-0c6b6f41ac03", "Goin Plumbing"),
    ("47b9f668-2734-4e0f-8f80-ab3159120abd", "sittigs-plumbing-llc-1770182567620-e0fc0a90", "e0fc0a90-615c-4f7e-ac9a-84f8d1d8cee8", "Sittigs Plumbing LLC"),
    ("bd84afdd-aeb6-4c67-a495-a278ef7f317f", "abc-cpas-1771101144448-6c66e06f", "6c66e06f-db39-455c-8920-f50ad93a4b42", "ABC CPAs"),
    ("44035586-6c70-41b3-af5c-8fbbacc0121f", "premier-plumbing-company-nyc-24-7-1770269849823-95b7c63a", "95b7c63a-fe36-442b-8b6d-15109d3279de", "Premier Plumbing Company"),
    ("7b0979b5-f390-4786-aad0-b4c1b5ae7afb", "m-d-plumbing-1770177584887-92940dee", "92940dee-56fb-45c2-9609-8256adf100d4", "MD Plumbing"),
    ("128262fa-11aa-4b6a-bf61-0772e3301a8a", "a-1-plumbing-co-1770275140995-2d98f4da", "2d98f4da-7225-4273-b7e8-61e2ba6e2b8d", "A Plumbing Co"),
    ("c5aa7cc8-7f43-463c-a99c-55dfb7fe2ec1", "florence-pet-clinic-1771107215496-f85c9b01", "f85c9b01-5273-48c1-aae8-aa7ed9d97f6a", "Florence Pet Clinic"),
]


def main():
    used = set()
    rows = []
    for site_id, subdomain, biz_id, biz_name in SITES:
        slug = gen_slug(biz_name)
        while slug in used:
            slug = gen_slug(biz_name)
        used.add(slug)
        dest_url = f"{SITE_BASE}/{subdomain}"
        short_url = f"{SHORTENER}/{slug}"
        link_id = str(uuid.uuid4())
        rows.append((link_id, slug, dest_url, biz_id, site_id, short_url))
        print(f"-- {slug}  {biz_name[:40]}")

    print()
    print("BEGIN;")
    print()

    vals = []
    for r in rows:
        v = f"('{r[0]}','{r[1]}','{r[2]}','site_preview','{r[3]}','{r[4]}',true,0,now(),now())"
        vals.append(v)
    print("INSERT INTO short_links (id,slug,destination_url,link_type,business_id,site_id,is_active,click_count,created_at,updated_at) VALUES")
    print(",\n".join(vals) + ";")
    print()

    for r in rows:
        print(f"UPDATE generated_sites SET short_url='{r[5]}' WHERE id='{r[4]}';")

    print()
    print("COMMIT;")


if __name__ == "__main__":
    main()
