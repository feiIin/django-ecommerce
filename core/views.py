from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from .models import Item, Order, OrderItem
from .forms import FeedbackForm
from django.utils import timezone

from churn import churn


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "product.html", context)


def checkout(request):
    return render(request, "checkout.html")


class FeedbackView(View):
    def get(self, *args, **kwargs):
        # form
        form = FeedbackForm()
        context = {
            'form': form
        }
        return render(self.request, "feedback.html", context)

    def post(self, *args, **kwargs):
        form = FeedbackForm(self.request.POST or None)
        if form.is_valid():
            print("The form is valid")
            timetable = form.cleaned_data['timetable']
            capacity = form.cleaned_data['capacity']
            time = form.cleaned_data['duration']
            facilities = form.cleaned_data['facilities']
            price = form.cleaned_data['price']
            dictionary = {'timetable': timetable, 'capacity': capacity, 'time': time,
                          'facilities': facilities, 'price': price}
            # This method is called after the user submit their answers.
            # This method should be the one that does the churn prediction for the current user
            # TODO: fill the method with the churn model. The method is in churn.py
            churn(dictionary)

        return redirect('core:feedback')


class HomeView(ListView):
    model = Item
    paginate_by = 5
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {'object': order}
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You don't have any class booked")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order is in order
        if order.items.filter(item__slug=item.slug).exists():
            messages.info(request, "You have already booked this class")
        else:
            messages.info(request, "You booked this class.")
            order.items.add(order_item)
            return redirect("core:product", slug=slug)
    else:
        order_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=order_date)
        order.items.add(order_item)
        messages.info(request, "You booked this class.")
    return redirect("core:product", slug=slug)


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            order.items.remove(order_item)
            messages.info(request, "You canceled this booking.")
            return redirect("core:product", slug=slug)
        else:
            messages.info(request, "You did not book this class.")
            return redirect("core:product", slug=slug)
    else:
        # add a message saying user doesn't have an order
        messages.info(request, "You have no classes booked")
        return redirect("core:product", slug=slug)