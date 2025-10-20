from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from tracker.models import Order


class Command(BaseCommand):
    help = "Auto-progress orders: created->in_progress after 10 minutes; complete inquiry orders 10 minutes after start."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=10,
            help="Age (in minutes) after which 'created' orders should progress to 'in_progress' (default: 10)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only report what would be updated",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max number of orders to process in this run (default: 500)",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)

        qs = (
            Order.objects.filter(status="created", created_at__lte=cutoff)
            .order_by("created_at")
        )
        total_candidates = qs.count()
        to_process = list(qs[:limit].values_list("id", flat=True))

        if not to_process:
            self.stdout.write(self.style.SUCCESS(f"No orders eligible for auto progression (checked {total_candidates})."))
            return

        self.stdout.write(f"Eligible orders: {total_candidates}. Processing up to {len(to_process)}…")

        now = timezone.now()
        updated = 0

        # Process in small batches to avoid long transactions
        batch_size = 100
        for i in range(0, len(to_process), batch_size):
            batch_ids = to_process[i : i + batch_size]
            if dry_run:
                # Simulate
                updated += len(batch_ids)
                continue
            with transaction.atomic():
                # Set status and started_at if not set
                rows = (
                    Order.objects.filter(id__in=batch_ids, status="created")
                    .update(status="in_progress", started_at=now)
                )
                updated += rows

        msg = f"Auto-progressed {updated} order(s) to in_progress."
        if dry_run:
            msg = "[DRY RUN] " + msg
        self.stdout.write(self.style.SUCCESS(msg))

        # Now also handle inquiry orders that have been in progress for at least <minutes>
        qs2 = (
            Order.objects.filter(type='inquiry', status='in_progress', started_at__lte=cutoff)
            .order_by('started_at')
        )
        total_inquiry = qs2.count()
        if total_inquiry == 0:
            self.stdout.write(self.style.SUCCESS("No inquiry orders eligible for auto-completion."))
            return

        updated2 = 0
        ids2 = list(qs2[:limit].values_list('id', 'started_at', 'created_at'))
        now2 = timezone.now()
        batch_size = 100
        for i in range(0, len(ids2), batch_size):
            batch = ids2[i:i+batch_size]
            id_list = [x[0] for x in batch]
            # Compute durations individually would require loop; set completed_at=now2, duration approx using SQL not trivial, so set to minutes since started in separate updates
            for oid, s_at, c_at in batch:
                try:
                    dur = int(((now2 - (s_at or c_at)).total_seconds()) // 60)
                except Exception:
                    dur = None
                with transaction.atomic():
                    rows = Order.objects.filter(id=oid, status='in_progress').update(status='completed', completed_at=now2, actual_duration=dur)
                    updated2 += rows
        self.stdout.write(self.style.SUCCESS(f"Auto-completed {updated2} inquiry order(s)."))
