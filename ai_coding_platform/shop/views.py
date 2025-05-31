from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PowerUp, Inventory
from accounts.models import Profile  

@login_required
def shop_view(request):
    powerups = PowerUp.objects.all()
    user_inventory = Inventory.objects.filter(user=request.user)
    inventory_dict = {inv.powerup.id: inv.quantity for inv in user_inventory}
    return render(request, 'shop/shop.html', {
        'powerups': powerups,
        'inventory': inventory_dict,
        'profile': request.user.profile,
    })

@login_required
def buy_powerup(request, powerup_id):
    if request.method == 'POST':
        try:
            powerup = PowerUp.objects.get(pk=powerup_id)
        except PowerUp.DoesNotExist:
            messages.error(request, "Power-up not found.")
            return redirect('shop')

        profile = request.user.profile
        if profile.coins < powerup.cost:
            messages.error(request, "Not enough coins to purchase this power-up.")
            return redirect('shop')

        # Deduct coins
        profile.coins -= powerup.cost
        profile.save()

        # Add the power-up to the user's inventory
        inventory, created = Inventory.objects.get_or_create(user=request.user, powerup=powerup)
        if not created:
            inventory.quantity += 1
            inventory.save()

        messages.success(request, f"Successfully purchased {powerup.name}!")
        return redirect('shop')
    else:
        messages.error(request, "Invalid reques.")
        return redirect('shop')
