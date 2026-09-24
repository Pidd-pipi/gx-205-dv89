import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LogicQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("number", "数字推理"),
                            ("figure", "图形推理"),
                            ("logic", "逻辑判断"),
                            ("analogy", "类比推理"),
                            ("deduction", "演绎推理"),
                        ],
                        max_length=32,
                    ),
                ),
                ("difficulty", models.CharField(max_length=16)),
                ("stem", models.TextField()),
                ("answer", models.CharField(max_length=32)),
                ("explanation", models.TextField()),
                ("knowledge", models.CharField(max_length=120)),
                ("image", models.ImageField(blank=True, upload_to="questions/")),
            ],
        ),
        migrations.CreateModel(
            name="ExamRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("total", models.PositiveIntegerField()),
                ("correct", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="UserProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("tier", models.CharField(default="青铜", max_length=16)),
                ("shield_available", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="TypeStat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("question_type", models.CharField(max_length=32)),
                ("answered", models.PositiveIntegerField(default=0)),
                ("correct", models.PositiveIntegerField(default=0)),
            ],
            options={
                "unique_together": {("user", "question_type")},
            },
        ),
        migrations.CreateModel(
            name="WrongBookEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="bank.logicquestion")),
                ("mistakes", models.PositiveIntegerField(default=1)),
                ("favorited", models.BooleanField(default=False)),
                ("last_practiced_at", models.DateField(auto_now=True)),
            ],
            options={
                "unique_together": {("user", "question")},
            },
        ),
    ]
