from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from trips.models import Trip
from trips.algorithms import calculate_settlement
from .models import Expense


@login_required
def expense_list(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk)
    expenses = trip.expenses.all()
    members = trip.members.all()

    # Per-category breakdown
    category_totals = {}
    for expense in expenses:
        cat = expense.get_category_display()
        category_totals[cat] = category_totals.get(cat, 0) + float(expense.amount)

    # Per-person spending
    person_totals = {}
    for member in members:
        paid = sum(float(e.amount) / e.payers.count()
                   for e in expenses if member in e.payers.all() and e.payers.count() > 0)
        owes = sum(e.get_share_per_person()
                   for e in expenses if member in e.split_among.all())
        person_totals[member.username] = {'paid': round(paid, 2), 'owes': round(owes, 2)}

    settlement = calculate_settlement(expenses, members)

    budget_pct = trip.get_budget_percentage()
    budget_color = trip.get_budget_color()

    return render(request, 'expenses/expense_list.html', {
        'trip': trip,
        'expenses': expenses,
        'members': members,
        'category_totals': category_totals,
        'person_totals': person_totals,
        'settlement': settlement,
        'budget_pct': budget_pct,
        'budget_color': budget_color,
        'total_spent': trip.get_total_spent(),
    })


@login_required
def expense_add(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk)
    members = trip.members.all()

    if request.method == 'POST':
        expense = Expense.objects.create(
            trip=trip,
            title=request.POST['title'],
            amount=float(request.POST['amount']),
            category=request.POST.get('category', 'misc'),
            date=request.POST.get('date') or None,
            notes=request.POST.get('notes', ''),
            receipt_description=request.POST.get('receipt_description', ''),
            created_by=request.user,
        )

        # Set payers
        payer_ids = request.POST.getlist('payers')
        if not payer_ids:
            payer_ids = [str(request.user.id)]
        from django.contrib.auth.models import User
        expense.payers.set(User.objects.filter(id__in=payer_ids))

        # Set split_among
        split_ids = request.POST.getlist('split_among')
        if not split_ids:
            expense.split_among.set(members)
        else:
            expense.split_among.set(User.objects.filter(id__in=split_ids))

        messages.success(request, f'Expense "{expense.title}" added (₹{expense.amount})')
        return redirect('expense_list', trip_pk=trip_pk)

    return render(request, 'expenses/expense_add.html', {
        'trip': trip,
        'members': members,
        'categories': Expense.CATEGORY_CHOICES,
    })


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    trip_pk = expense.trip.pk
    name = expense.title
    expense.delete()
    messages.success(request, f'Expense "{name}" removed.')
    return redirect('expense_list', trip_pk=trip_pk)
