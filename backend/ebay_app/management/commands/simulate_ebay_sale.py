"""Management command that simulates an eBay sale or cancellation in the sandbox."""

from django.core.management.base import BaseCommand, CommandError

from ebay_app.services.simulation import SimulationError, simulate_cancellation, simulate_sale

NO_TARGET = "Bitte eine Artikelnummer angeben oder --cancel <Bestell-ID> verwenden."


class Command(BaseCommand):
    """
    Simulate what eBay reports after a sale.

    - simulate_ebay_sale <SKU> [--quantity N]: create a paid eBay order for the product.
    - simulate_ebay_sale --cancel <order id>: cancel a simulated order as eBay would report it.
    """

    help = "Simulate an eBay sale (or its cancellation) in the sandbox."

    def add_arguments(self, parser):
        """Register the SKU, the quantity and the cancel option."""
        parser.add_argument("sku", nargs="?", help="SKU of the product to sell")
        parser.add_argument("--quantity", type=int, default=1, help="number of units sold (default 1)")
        parser.add_argument("--cancel", type=int, metavar="ORDER_ID", help="id of a simulated order to cancel")

    def handle(self, *args, **options):
        """Run the sale or the cancellation and report the resulting order."""
        if not options["sku"] and not options["cancel"]:
            raise CommandError(NO_TARGET)
        try:
            order = self._run(options)
        except SimulationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(self._summary(order)))

    def _run(self, options):
        """Dispatch to the cancellation or the sale."""
        if options["cancel"]:
            return simulate_cancellation(options["cancel"])
        return simulate_sale(options["sku"], options["quantity"])

    def _summary(self, order):
        """Return a one-line description of the order for the terminal."""
        status = order.get_fulfillment_status_display()
        return f"Bestellung #{order.pk} ({order.ebay_order_id}) – {order.buyer_name}, {order.ship_city} – {status}"
