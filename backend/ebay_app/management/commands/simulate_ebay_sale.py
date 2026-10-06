"""Management command that simulates an eBay sale, payment or cancellation in the sandbox."""

from django.core.management.base import BaseCommand, CommandError

from ebay_app.services.simulation import (
    SimulationError,
    simulate_cancellation,
    simulate_payment,
    simulate_sale,
)

NO_TARGET = "Bitte eine Artikelnummer angeben oder --pay / --cancel <Bestell-ID> verwenden."


class Command(BaseCommand):
    """
    Simulate what eBay reports after a sale.

    - simulate_ebay_sale <SKU> [--quantity N] [--unpaid]: create an eBay order for the product.
    - simulate_ebay_sale --pay <order id>: report the payment of a simulated order.
    - simulate_ebay_sale --cancel <order id>: cancel a simulated order as eBay would report it.
    """

    help = "Simulate an eBay sale (or its payment or cancellation) in the sandbox."

    def add_arguments(self, parser):
        """Register the SKU and the options."""
        parser.add_argument("sku", nargs="?", help="SKU of the product to sell")
        parser.add_argument("--quantity", type=int, default=1, help="number of units sold (default 1)")
        parser.add_argument("--unpaid", action="store_true", help="create the order with an open payment")
        parser.add_argument("--pay", type=int, metavar="ORDER_ID", help="id of a simulated order to mark as paid")
        parser.add_argument("--cancel", type=int, metavar="ORDER_ID", help="id of a simulated order to cancel")

    def handle(self, *args, **options):
        """Run the requested simulation and report the resulting order."""
        if not (options["sku"] or options["pay"] or options["cancel"]):
            raise CommandError(NO_TARGET)
        try:
            order = self._run(options)
        except SimulationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(self._summary(order)))

    def _run(self, options):
        """Dispatch to the cancellation, the payment or the sale."""
        if options["cancel"]:
            return simulate_cancellation(options["cancel"])
        if options["pay"]:
            return simulate_payment(options["pay"])
        return simulate_sale(options["sku"], options["quantity"], paid=not options["unpaid"])

    def _summary(self, order):
        """Return a one-line description of the order for the terminal."""
        state = f"{order.get_fulfillment_status_display()}, {order.get_payment_status_display()}"
        return f"Bestellung #{order.pk} ({order.ebay_order_id}) – {order.buyer_name}, {order.ship_city} – {state}"
