from collections import Counter
from django.contrib.auth import login, logout, authenticate
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Count, Value, Max, Avg, Subquery, OuterRef, F
from django.db.models.query_utils import Q
from django.db.models.functions import Coalesce
from myapp.forms import (
    LoginForm, RegisterForm, AddHivesPlace, AddHive, AddMother, AddVisit,
    ChangeHivesPlace, ChangeMotherHive, EditVisit, EditHivesPlace
)
from myapp.models import Hives, HivesPlaces, Beekeepers, Visits, Mothers, Tasks


def index(request):
    if request.user.is_authenticated:
        return redirect('overview')
    return render(request, 'home.html')


def login_user(request):
    if request.user.is_authenticated:
        messages.warning(request, 'Jste již přihlášen.')
        return redirect('overview')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Přihlášení proběhlo úspěšně.')
                return redirect('overview')
            else:
                messages.error(request, 'Neplatné přihlašovací údaje.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_user(request):
    logout(request)
    messages.success(request, 'Odhlášení proběhlo úspěšně.')
    return redirect('index')


def signup(request):
    if request.user.is_authenticated:
        messages.warning(request, 'Pro registraci nového uživatele se musíte nejprve odhlásit.')
        return redirect('overview')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=username, password=password)
            login(request, user)
            messages.success(request, 'Registrace nového uživatele proběhla úspěšně, nyní jste přihlášen.')
            return redirect('overview')
    else:
        form = RegisterForm()
    return render(request, 'signup.html', {'form': form})


def login_required_message(request):
    messages.error(request, 'Obsah je dostupný jen přihlášeným uživatelům.')
    return redirect('login_user')


@login_required
def overview(request):
    # Přehled aktivních stanovišť
    hives_places_count = HivesPlaces.objects.filter(beekeeper=request.user, active=True).count()
    hives_count = Hives.objects.filter(place__beekeeper=request.user, active=True).count()
    hives_places = HivesPlaces.objects.filter(beekeeper=request.user, active=True)
    results_to_dicts = HivesPlaces.objects.filter(beekeeper=request.user, active=True).annotate(
        avg_honey_yield=Avg('hives__visits__honey_yield'),
        avg_condition=Avg('hives__visits__condition'),
    )

    avg_honey_yield_dict = {result.name: result.avg_honey_yield for result in results_to_dicts}
    avg_condition_dict = {result.name: result.avg_condition for result in results_to_dicts}

    hives_places_dict = (
        HivesPlaces.objects
        .filter(beekeeper=request.user, active=True)
        .annotate(hives_count=Coalesce(Count('hives', filter=Q(hives__active=True), distinct=True), Value(0)))
        .values('name', 'hives_count')
    )
    hives_places_dict = {item['name']: item['hives_count'] for item in hives_places_dict}

    mothers_count_list = (
        Mothers.objects
        .filter(Q(hive__active=True), hive__place__beekeeper=request.user, active=True)
        .annotate(mothers_count=Coalesce(Count('id', distinct=True), Value(0)))
        .values('hive__place__name', 'mothers_count')
    )

    mothers_count_dict = {}
    for item in mothers_count_list:
        place_name = item['hive__place__name']
        mothers_count = item['mothers_count']  # Corrected variable name

        if place_name in mothers_count_dict:
            mothers_count_dict[place_name] += mothers_count
        else:
            mothers_count_dict[place_name] = mothers_count

    # Poslední návštěvy na aktivních stanovištích
    last_visit_date = (
        Visits.objects
        .filter(hive__place__beekeeper=request.user, active=True)
        .values('hive__place__name')
        .annotate(last_visit=Max('date'))
    )

    last_visit_date = {item['hive__place__name']: item['last_visit'] for item in last_visit_date}

    # Naposledy provedené úkony během návštěvy včelstva
    last_tasks_subquery = Visits.objects.filter(
        hive__place=OuterRef('pk'),
        hive__active=True,
        active=True,
        performed_tasks__isnull=False
    ).order_by('-date', 'hive__number').values(last_performed_task=ArrayAgg('performed_tasks__name'))[:1]

    places_with_last_performed_tasks = HivesPlaces.objects.filter(
        beekeeper=request.user,
        active=True
    ).annotate(
        last_performed_tasks=Subquery(last_tasks_subquery)
    ).values('name', 'last_performed_tasks')

    tasks_dict = {item['name']: item['last_performed_tasks'] for item in places_with_last_performed_tasks}

    # Vytvoření slovníku průměrných hodnot 'mite_drop' pro jednotlivá stanoviště
    last_mite_drop_subquery = (
        Visits.objects
        .filter(
            hive=OuterRef('pk'),
            mite_drop__isnull=False,
            active=True
        )
        .order_by('-date')
        .values('mite_drop')[:1]
    )

    places_with_avg_mite_drop = Hives.objects.filter(
        place__beekeeper=request.user,
        active=True,
    ).annotate(
        avg_mite_drop=Subquery(last_mite_drop_subquery)
    ).exclude(
        avg_mite_drop__isnull=True
    ).values('place__name').annotate(
        avg_mite_drop=Avg('avg_mite_drop')
    )

    mite_drop_dict = {item['place__name']: item['avg_mite_drop'] for item in places_with_avg_mite_drop}

    # Vytvoření slovníků pro poslední datum aplikace léčiva
    last_medication_subquery = Visits.objects.filter(
        hive__place=OuterRef('pk'),
        medication_application__gt='',
        active=True
    ).order_by('-date').values('medication_application', 'date')[:1]

    places_with_last_medical_application = HivesPlaces.objects.filter(
        beekeeper=request.user,
        active=True,
    ).annotate(
        last_medication=Subquery(last_medication_subquery.values('medication_application')),
        last_medication_date=Subquery(last_medication_subquery.values('date'))
    ).values('name', 'last_medication', 'last_medication_date')

    medical_application_dict = {item['name']: item['last_medication']
                                for item in places_with_last_medical_application}
    medical_application_date_dict = {item['name']: item['last_medication_date']
                                     for item in places_with_last_medical_application}

    # Varování před smazáním stanoviště s aktivními včelstvy
    warning = "Chystáte se odstranit stanoviště i se včelstvy. " \
              "Pokud chcete včelstva zachovat, nejprve je přemístěte na jiné stanoviště."

    # Vykreslení šablony iverview a předání všech potřebných dat
    return render(request, 'overview.html', {
        'hives_places_count': hives_places_count,
        'hives_count': hives_count,
        'mothers_count_dict': mothers_count_dict,
        'avg_honey_yield_dict': avg_honey_yield_dict,
        'avg_condition_dict': avg_condition_dict,
        'mite_drop_dict': mite_drop_dict,
        'hives_places': hives_places,
        'hives_places_dict': hives_places_dict,
        'medical_application_dict': medical_application_dict,
        'medical_application_date_dict': medical_application_date_dict,
        'tasks_dict': tasks_dict,
        'last_visit_date': last_visit_date,
        'warning': warning
    })


def get_next_hive_number(hives_place_id):
    used_numbers = Hives.objects.filter(place__id=hives_place_id, active=True).values_list('number', flat=True)
    current_number = 1
    while current_number in used_numbers:
        current_number += 1

    return current_number


@login_required
def hives_place(request, hives_place_id=None):
    try:
        # Získání aktivního stanoviště
        user_hives_place = get_object_or_404(HivesPlaces, id=hives_place_id, beekeeper=request.user, active=True)
        hives = Hives.objects.filter(place=user_hives_place, active=True)
        hives_count = hives.count()

        # Poslední návštěvy na aktivních včelstvech na stanovišti
        last_visits = (
            Visits.objects
            .filter(hive__place__beekeeper=request.user, hive__place=hives_place_id, active=True)
            .values('hive__id', 'hive_body_size', 'honey_supers_size', 'condition')
            .annotate(last_visit=Max('date'))
        )
        last_visits_date = {item['hive__id']: item['last_visit'] for item in last_visits}
        hive_size = {item['hive__id']: f"{item['hive_body_size']}+{item['honey_supers_size']}" for item in last_visits}
        hive_condition = {item['hive__id']: item['condition'] for item in last_visits}

        # Získání matky pro aktivní včelstvo
        hives_dict = {}
        mothers_dict = {}
        years_dict = {}
        for hive in hives:
            mother = (
                Mothers.objects
                .filter(hive=hive, active=True)
                .first()
            )

            if mother:
                hives_dict[hive.id] = mother.mark
                mothers_dict[hive.id] = mother.id
                years_dict[hive.id] = mother.year
            else:
                hives_dict[hive.id] = None

        # slovník poslední hodnoty medného výnosu zaznamenané při prohlídkách včelstev na stanovišti
        last_honey_yield_dict = {
            hive.id: {'value': hive.last_honey_yield().honey_yield if hive.last_honey_yield() else None,
                      'date': hive.last_honey_yield().date if hive.last_honey_yield() else None}
            for hive in hives
        }

        # slovník poslední hodnoty spadu roztočů zaznamenané při prohlídkách včelstev na stanovišti
        last_mite_drop_dict = {
            hive.id: {'value': hive.last_mite_drop().mite_drop if hive.last_mite_drop() else None,
                      'date': hive.last_mite_drop().date if hive.last_mite_drop() else None}
            for hive in hives
        }

        # slovník poslední aplikace léčiva při prohlídkách včelstev na stanovišti
        last_medication_application_dict = {}
        for hive in hives:
            last_medication_application_dict[hive.id] = {
                'value': (
                    hive.last_medication_application().medication_application
                    if hive.last_medication_application() else None
                ),
                'date': hive.last_medication_application().date if hive.last_medication_application() else None
            }

        # slovník poslední příznaky nemoci při prohlídkách včelstev na stanovišti
        last_disease_dict = {
            hive.id: {'value': hive.last_disease().disease if hive.last_disease() else None,
                      'date': hive.last_disease().date if hive.last_disease() else None}
            for hive in hives
        }

        # slovník poslední komentář při prohlídkách včelstev na stanovišti
        last_comment_dict = {
            hive.id: {'value': hive.last_comment().comment if hive.last_comment() else None,
                      'date': hive.last_comment().date if hive.last_comment() else None}
            for hive in hives
        }

        form = ChangeHivesPlace(user=request.user, hives_place_id=hives_place_id)
        return render(request, 'overview.html', {
            'overview_spec': 'hives',
            'hives': hives,
            'hives_count': hives_count,
            'hives_dict': hives_dict,
            'mothers_dict': mothers_dict,
            'years_dict': years_dict,
            'hives_place_id': hives_place_id,
            'hives_place_name': user_hives_place.name,
            'last_visits': last_visits,
            'last_visits_date': last_visits_date,
            'hive_size': hive_size,
            'hive_condition': hive_condition,
            'last_honey_yield_dict': last_honey_yield_dict,
            'last_mite_drop_dict': last_mite_drop_dict,
            'last_medication_application_dict': last_medication_application_dict,
            'last_disease_dict': last_disease_dict,
            'last_comment_dict': last_comment_dict,
            'form': form
        })
    except Http404:
        messages.error(request, "Záznamy o včelstvu pro přihlášeného uživatele nejsou k dispozici.")
        return redirect('overview')


@login_required
def add_hives_place(request):
    if request.method == 'POST':
        form = AddHivesPlace(request.POST)
        if form.is_valid():
            # Získání aktuálně přihlášeného uživatele
            beekeeper_id = Beekeepers.objects.get(user_ptr__username=request.user.username)

            # Uložení nového záznamu do databáze
            hives_place = form.save(commit=False)
            hives_place.beekeeper = beekeeper_id  # Přiřazení přihlášeného uživatele
            hives_place.save()
            messages.success(request, 'Nové stanoviště bylo vytvořeno.')
            return redirect('overview')  # Přesměrování na domovskou stránku nebo jinam po úspěšném vytvoření
    else:
        form = AddHivesPlace()

    return render(request, 'create_hives_place.html', {'form': form})


@login_required
def remove_hives_place(request, hives_place_id=None):
    try:
        hives_place = get_object_or_404(HivesPlaces, beekeeper=request.user, id=hives_place_id, active=True)
    except Http404:
        messages.error(request, "Úprava záznamů pro přihlášeného uživatele není možná.")
        return redirect('overview')

    with transaction.atomic():
        # Deaktivace stanoviště
        hives_place.active = False
        hives_place.save()

        # Získání všech včelstev na stanovišti
        hives_in_place = hives_place.hives.all()

        # Deaktivace všech včelstev, matek a návštěv
        Hives.objects.filter(id__in=hives_in_place).update(active=False)
        Mothers.objects.filter(hive__in=hives_in_place).update(active=False)
        Visits.objects.filter(hive__in=hives_in_place).update(active=False)

    if hives_place.hives.count() > 0:
        messages.success(request, f'Stanoviště {hives_place.name} bylo úspěšně smazáno včetně jeho včelstev.')
    else:
        messages.success(request, f'Stanoviště {hives_place.name} bylo úspěšně smazáno.')
    return redirect('overview')


@login_required
def edit_hives_place(request, hives_place_id):
    try:
        user_hives_place = get_object_or_404(HivesPlaces, beekeeper=request.user, id=hives_place_id, active=True)
    except Http404:
        messages.error(request, "Záznamy o vybraném stanivšti pro přihlášeného uživatele nejsou k dispozici...")
        return redirect('overview')

    if request.method == 'POST':
        form = EditHivesPlace(request.POST, instance=user_hives_place)
        if form.is_valid():
            form.save()
            messages.success(request, "Editace stanoviště proběhla úspěšně.")
            return redirect('overview')

    else:
        form = EditHivesPlace(instance=user_hives_place)

    return render(request, 'create_hives_place.html', {'form': form})


@login_required
def add_hive(request, hives_place_id=None):
    try:
        hives_place = get_object_or_404(HivesPlaces, id=hives_place_id, active=True)
    except Http404:
        messages.error(request, "Záznamy o stanovišti pro přihlášeného uživatele nejsou k dispozici.")
        return redirect('overview')

    # Kontrola, zda přihlášený uživatel odpovídá beekeeperovi v HivesPlaces
    if request.user.id != hives_place.beekeeper.id:
        messages.error(request, 'Nemáte oprávnění přidávat včelstvo na toto stanoviště.')
        return redirect('overview')

    if request.method == 'POST':
        form = AddHive(request.POST)
        if form.is_valid():
            hive = form.save(commit=False)
            hive.number = get_next_hive_number(hives_place_id)
            hive.place_id = hives_place.id
            hive.save()
            messages.success(request, f'Bylo vytvořeno včelstvo č. {hive.number} '
                                      f'na stanovišti {hives_place.name}')
            return redirect('hives_place', hives_place_id)
    else:
        form = AddHive()

    return render(request, 'create_hive.html', {'form': form})


@login_required
def remove_hive(request, hive_id=None):
    try:
        hive = get_object_or_404(Hives, place__beekeeper=request.user, id=hive_id, active=True)
    except Http404:
        messages.error(request, "Úprava záznamů o včelstvu pro přihlášeného uživatele není možná.")
        return redirect('overview')

    with transaction.atomic():
        # Deaktivace stanoviště
        hive.active = False
        hive.save()

        # Deaktivace matky a návštěv
        Mothers.objects.filter(hive=hive).update(active=False)
        Visits.objects.filter(hive=hive).update(active=False)

        messages.success(request, f'Včelstvo {hive.number} na stanovišti {hive.place.name} bylo úspěšně smazáno.')
    return redirect('hives_place', hive.place_id)


@login_required
def move_hive(request, old_hives_place):
    try:
        user = request.user
        hive_ids = Hives.objects.filter(place__beekeeper=user, active=True)
        hive_place_ids = list(HivesPlaces.objects.filter(beekeeper=user, active=True).values_list('id', flat=True))
        old_hives_place = HivesPlaces.objects.filter(id=old_hives_place).first()

        if request.method == 'POST':
            form = ChangeHivesPlace(user=request.user, hives_place_id=old_hives_place.id, data=request.POST)
            if form.is_valid():
                selected_hive_ids = form.cleaned_data['selected_hives']
                new_hives_place = form.cleaned_data['new_hives_place']

                if not set(selected_hive_ids).issubset(set(hive_ids)) or new_hives_place.id not in hive_place_ids:
                    messages.error(request, f"Vybraná včelstva nebo nové stanoviště nepatří přihlášenému uživateli.")
                    return redirect('overview')
                new_numbers = []
                with transaction.atomic():
                    for selected_hive_id in selected_hive_ids:
                        selected_hive = Hives.objects.get(id=selected_hive_id.id)
                        selected_hive.place = new_hives_place
                        selected_hive.number = get_next_hive_number(new_hives_place.id)
                        new_numbers.append(selected_hive.number)
                        selected_hive.save()

                    messages.success(request, f'Včelstva ({", ".join(map(str, selected_hive_ids))}'
                                              f') byla přemístěna ze stanoviště {old_hives_place.name}'
                                              f' na stanoviště {new_hives_place.name}'
                                              f' a očíslována({", ".join(map(str, new_numbers))}).'
                                     )
                    return redirect('hives_place', new_hives_place.id)
            else:
                messages.error(request, 'Nevybral jste žádná včelstva k přemístění.')
        else:
            return redirect('hives_place', old_hives_place.id)
    except Http404:
        messages.error(request, "Úprava záznamů o včelstvu není možná.")
        return redirect('hives_place', old_hives_place.id)

    return redirect('hives_place', old_hives_place.id)


@login_required
def mothers(request, mother_id=None):
    try:
        mother = get_object_or_404(Mothers, id=mother_id, hive__place__beekeeper=request.user)
        ancestors = []
        current_ancestor = mother.ancestor
        while current_ancestor:
            ancestors.append(current_ancestor)
            current_ancestor = current_ancestor.ancestor

        descendants = Mothers.objects.filter(ancestor=mother_id)
        sisters = Mothers.objects.filter(ancestor=mother.ancestor, ancestor__isnull=False).exclude(id=mother.id)

        form = ChangeMotherHive(user=request.user, mother=mother)

        return render(request, 'overview.html', {
            'overview_spec': 'mothers',
            'mother': mother,
            'ancestors': ancestors,
            'descendants': descendants,
            'sisters': sisters,
            'form': form
        })

    except Http404:
        messages.error(request, "Záznamy o matce pro přihlášeného uživatele nejsou k dispozici.")
        return redirect('overview')


@login_required
def remove_mother(request, mother_id=None):
    try:
        mother = get_object_or_404(Mothers, hive__place__beekeeper=request.user, id=mother_id, active=True)
    except Http404:
        messages.error(request, "Úprava záznamů o matce pro přihlášeného uživatele není možná.")
        return redirect('overview')

    with transaction.atomic():
        # Deaktivace matky
        mother.active = False
        mother.save()

        messages.success(request, f'Matka {mother.mark} na stanovišti {mother.hive.place.name} byla zrušena.')
    return redirect('hives_place', mother.hive.place_id)


@login_required
def erase_mother(request, mother_id=None):
    try:
        mother = get_object_or_404(Mothers, id=mother_id, hive__place__beekeeper=request.user, active=False)
        mother.delete()
        messages.success(request, f'Záznamy o matce {mother.mark}({mother.year}) byly úspěšně odstraněny.')

    except Http404:
        messages.error(request, "Záznamy o matce pro přihlášeného uživatele nejsou k dispozici.")
    return redirect('overview')


@login_required
def move_mother(request, mother_id=None):
    try:
        user = request.user
        mother = Mothers.objects.get(hive__place__beekeeper=user, active=True, id=mother_id)

        if request.method == 'POST':
            form = ChangeMotherHive(data=request.POST, user=user, mother=mother)
            if form.is_valid():

                new_hive = form.cleaned_data['new_hive']

                with transaction.atomic():
                    if mother.hive_id:
                        old_hive = Hives.objects.get(id=mother.hive_id)
                        old_hive.mother = None
                        old_hive.save()

                        mother.hive_id = new_hive.id
                        mother.save()

                        messages.success(request, f"Matka {mother.mark} byla úspěšně přemístěna do včelstva č."
                                                  f"{new_hive.number} na stanovišti {new_hive.place.name}.")
                    return redirect('hives_place', new_hive.place_id)
            else:
                messages.error(request, form.errors)
    except Exception as e:
        messages.error(request, f'Chyba při přemisťování matky: {e}')

    return redirect('mothers', mother_id)


@login_required
def add_mother(request, hive_id=None):
    try:
        selected_hive = get_object_or_404(Hives, id=hive_id, active=True)
    except Http404:
        messages.error(request, "Uživatel může přidávat matky pouze do svých včelstev.")
        return redirect('overview')

    if request.user.id != selected_hive.place.beekeeper.id:
        messages.error(request, 'Nemáte oprávnění přidávat matku do požadovaného včelstva.')
        return redirect('overview')

    if request.method == 'POST':
        form = AddMother(request.user, request.POST)
        if form.is_valid():
            mother = form.save(commit=False)
            mother.hive = selected_hive
            mother.save()
            messages.success(request, f'Matka byla přidána do včelstva {selected_hive.number} '
                                      f'na stanovišti {selected_hive.place.name} .'
                             )
            return redirect('hives_place', selected_hive.place.id)
    else:
        form = AddMother(request.user)

    return render(request, 'create_mother.html', {'form': form})


@login_required
def edit_mother(request, mother_id=None):
    try:
        selected_mother = get_object_or_404(Mothers, id=mother_id, hive__place__beekeeper=request.user, active=True)
    except Http404:
        messages.error(request, "Uživatel může editovat údaje pouze o svých matkách.")
        return redirect('overview')

    if request.method == 'POST':
        form = AddMother(request.user, request.POST, instance=selected_mother)
        if form.is_valid():
            form.save()
            messages.success(request, f'Údaje o matce {selected_mother.mark}'
                                      f' ve včelstvu {selected_mother.hive.number} '
                                      f'na stanovišti {selected_mother.hive.place.name} '
                                      f'byly aktualizovány.'
                             )
            return redirect('hives_place', selected_mother.hive.place.id)
    else:
        form = AddMother(request.user, instance=selected_mother)

    return render(request, 'create_mother.html', {
        'form': form,
        'selected_mother': selected_mother
    })


@login_required
def visits(request, hive_id=None):
    try:
        user_hive = get_object_or_404(Hives, id=hive_id, place__beekeeper=request.user)
        user_visits = Visits.objects.filter(hive=user_hive, active=True).order_by('-date')
        user_hive.mother = Mothers.objects.filter(hive=user_hive, active=True)

        return render(request, 'overview.html', {
            'overview_spec': 'visits',
            'hive_id': hive_id,
            'user_hive': user_hive,
            'user_visits': user_visits
        })
    except Http404:
        messages.error(request, "Záznamy o včelstvu pro přihlášeného uživatele nejsou k dispozici.")
        return redirect('overview')


@login_required
def add_visit(request, hive_id=None):
    try:
        user_hive = get_object_or_404(Hives, id=hive_id, place__beekeeper=request.user, active=True)
        user_hive.mother = Mothers.objects.filter(hive=user_hive, active=True)
    except Http404:
        messages.error(request, "Záznamy o vybraném včelstvu nejsou k dispozici.")
        return redirect('overview')

    if request.user.id != user_hive.place.beekeeper.id:
        messages.error(request, "Uživatel může zapisovat prohlídky pouze u svých včelstev.")
        return redirect('overview')

    if request.method == 'POST':
        form = AddVisit(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.hive_id = user_hive.id
            visit.save()
            visit.performed_tasks.add(*form.cleaned_data['performed_tasks'])
            messages.success(request, f'U včelstva {user_hive.number} '
                                      f'na stanovišti {user_hive.place.name} '
                                      f'byla zapsána prohlídka.')
            return redirect('visits', user_hive.id)
    else:
        try:
            latest_visit = Visits.objects.filter(
                hive__place__beekeeper=request.user,
                hive_id=hive_id,
                active=True
            ).aggregate(latest_visit_date=Max('date'))['latest_visit_date']

            visit_instance = get_object_or_404(
                Visits,
                hive__place__beekeeper=request.user,
                hive_id=hive_id,
                date=latest_visit,
                active=True
            )

            form_data = {
                'condition': visit_instance.condition,
                'hive_body_size': visit_instance.hive_body_size,
                'honey_supers_size': visit_instance.honey_supers_size,
            }

            form = AddVisit(initial=form_data)
        except Http404:
            form = AddVisit()

    return render(request, 'create_visit.html', {
        'form': form,
        'user_hive': user_hive
    })


@login_required
def remove_visit(request, visit_id=None):
    try:
        user = request.user
        visit = get_object_or_404(Visits, id=visit_id, hive__place__beekeeper=user, active=True)

        with transaction.atomic():
            visit.active = False
            visit.save()

        formatted_date = visit.date.strftime('%d. %m. %Y')
        messages.success(request, f"Prohlídka z {formatted_date} byla smazána.")
        return redirect('visits', visit.hive_id)

    except Http404:
        messages.error(request, f"Záznam o prohlídce přihlášeného uživatele neexistuje.")
    return redirect('overview')


@login_required
def edit_visit(request, visit_id):
    try:
        user_hive = get_object_or_404(Hives, visits__id=visit_id, place__beekeeper=request.user, active=True)
        visit_instance = get_object_or_404(Visits, id=visit_id, hive__place__beekeeper=request.user, active=True)
    except Http404:
        messages.error(request, "Požadované záznamy o vybraném včelstvu nejsou k dispozici...")
        return redirect('overview')

    if request.method == 'POST':
        form = EditVisit(request.POST, instance=visit_instance)
        if form.is_valid():
            form.save()
            form.instance.performed_tasks.set(form.cleaned_data['performed_tasks'])
            messages.success(request, f'Prohlídka u včelstva {visit_instance.hive.number} '
                                      f'na stanovišti {visit_instance.hive.place.name} '
                                      f'byla úspěšně upravena.')
            return redirect('visits', user_hive.id)

    else:
        form = EditVisit(instance=visit_instance)

    return render(request, 'create_visit.html', {
        'form': form,
        'visit_instance': visit_instance,
        'user_hive': user_hive
    })
