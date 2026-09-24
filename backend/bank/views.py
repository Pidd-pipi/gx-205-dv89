from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from bank.models import ExamRecord, TypeStat, UserProgress
from bank.serializers import GeneratePaperSerializer, SubmitExamSerializer


QUESTIONS = [
    {
        "id": 101,
        "type": "数字推理",
        "difficulty": "中级",
        "stem": "2，6，12，20，30，下一项是多少？",
        "options": ["38", "40", "42", "44"],
        "answer": "42",
        "explanation": "相邻差为 4、6、8、10，下一差为 12，因此答案为 42。",
        "knowledge": "二级等差",
    },
    {
        "id": 102,
        "type": "逻辑判断",
        "difficulty": "中级",
        "stem": "所有通过高阶训练的人都完成错题复盘，小林完成高阶训练，可推出什么？",
        "options": ["小林完成错题复盘", "小林没有错题", "小林排名第一", "无法判断"],
        "answer": "小林完成错题复盘",
        "explanation": "这是充分条件推理：完成高阶训练可以推出完成错题复盘。",
        "knowledge": "充分条件",
    },
    {
        "id": 103,
        "type": "类比推理",
        "difficulty": "初级",
        "stem": "医生：诊断，相当于教师：？",
        "options": ["备课", "授课", "批改", "讲解"],
        "answer": "授课",
        "explanation": "职业与核心工作行为对应，医生核心行为是诊断，教师核心行为是授课。",
        "knowledge": "职业关系",
    },
]

# 全部题型与雷达轴的对应关系，顺序即首页展示顺序
QUESTION_TYPES = ["数字推理", "图形推理", "逻辑判断", "类比推理", "演绎推理"]
RADAR_AXES = {
    "数字推理": "数字",
    "图形推理": "图形",
    "逻辑判断": "逻辑",
    "类比推理": "类比",
    "演绎推理": "演绎",
}

# 段位由低到高，门槛为最近五套练习总正确率（%）
TIER_LADDER = ["青铜", "白银", "黄金", "铂金", "钻石", "王者"]
TIER_THRESHOLDS = {"青铜": 0, "白银": 60, "黄金": 70, "铂金": 80, "钻石": 90, "王者": 95}
RECENT_PAPER_LIMIT = 5


def recent_accuracy(user) -> float | None:
    """最近五套练习的总正确率（按题数加权），没有记录时返回 None。"""
    records = ExamRecord.objects.filter(user=user).order_by("-created_at", "-id")[:RECENT_PAPER_LIMIT]
    total = sum(record.total for record in records)
    if not total:
        return None
    correct = sum(record.correct for record in records)
    return round(correct / total * 100, 1)


def settle_tier(progress: UserProgress) -> tuple[float | None, str]:
    """按最近五套总正确率结算段位，返回 (总正确率, 事件)。

    事件为 "promoted" / "protected" / "demoted" / ""：
    - 达到更高段位门槛：当场晋级（可跨级），保护次数重置；
    - 低于当前段位门槛：先消耗一次保护，保护已用完才下降一段；
    - 回到门槛之上：保护次数恢复。
    """
    rate = recent_accuracy(progress.user)
    if rate is None:
        return None, ""

    current = TIER_LADDER.index(progress.tier)
    qualified = max(
        index for index, name in enumerate(TIER_LADDER) if rate >= TIER_THRESHOLDS[name]
    )

    if qualified > current:
        progress.tier = TIER_LADDER[qualified]
        progress.shield_available = True
        progress.save(update_fields=["tier", "shield_available"])
        return rate, "promoted"

    if rate < TIER_THRESHOLDS[progress.tier]:
        if progress.shield_available:
            progress.shield_available = False
            progress.save(update_fields=["shield_available"])
            return rate, "protected"
        progress.tier = TIER_LADDER[current - 1]
        progress.shield_available = True
        progress.save(update_fields=["tier", "shield_available"])
        return rate, "demoted"

    if not progress.shield_available:
        progress.shield_available = True
        progress.save(update_fields=["shield_available"])
    return rate, ""


def rank_hint_for(progress: UserProgress | None, rate: float | None, event: str) -> str:
    if progress is None:
        return "登录后交卷成绩才会计入学习进度与段位结算。"
    rate_text = f"{rate:.1f}"
    if event == "promoted":
        return f"最近五套总正确率 {rate_text}%，达到门槛，当场晋级【{progress.tier}】！"
    if event == "protected":
        return f"最近五套总正确率 {rate_text}%，低于【{progress.tier}】保段线，段位保护已生效，再低于门槛一次将掉段。"
    if event == "demoted":
        return f"最近五套总正确率 {rate_text}%，再次低于保段线，段位下降至【{progress.tier}】。"
    return f"最近五套总正确率 {rate_text}%，当前段位【{progress.tier}】。"


def build_dashboard(user) -> dict:
    stats = {}
    progress = None
    if user is not None:
        stats = {stat.question_type: stat for stat in TypeStat.objects.filter(user=user)}
        progress, _ = UserProgress.objects.get_or_create(user=user)

    categories = []
    radar = []
    total_answered = 0
    total_correct = 0
    for index, type_name in enumerate(QUESTION_TYPES, start=1):
        stat = stats.get(type_name)
        answered = stat.answered if stat else 0
        correct = stat.correct if stat else 0
        # 没有作答记录的题型不计零分，雷达与分类都按暂无数据处理
        accuracy = round(correct / answered * 100, 1) if answered else None
        categories.append({"id": index, "name": type_name, "accuracy": accuracy, "total": answered})
        radar.append({"axis": RADAR_AXES[type_name], "value": accuracy})
        total_answered += answered
        total_correct += correct

    correct_rate = round(total_correct / total_answered * 100, 1) if total_answered else 0
    nickname = user.username if user is not None else "未登录访客"
    tier = progress.tier if progress else "青铜"

    return {
        "profile": {
            "nickname": nickname,
            "tier": tier,
            "totalAnswered": total_answered,
            "correctRate": correct_rate,
            "streakDays": 0,
            "practiceMinutes": 0,
        },
        "categories": categories,
        "paper": QUESTIONS,
        "wrongBook": [
            {"id": 1, "title": "集合包含关系反推", "type": "演绎推理", "mistakes": 5, "lastPracticed": "05-28"},
            {"id": 2, "title": "九宫格旋转规律", "type": "图形推理", "mistakes": 4, "lastPracticed": "05-27"},
            {"id": 3, "title": "多条件排序", "type": "逻辑判断", "mistakes": 3, "lastPracticed": "05-26"},
        ],
        "rankings": [
            {"rank": 1, "name": "ReasonMax", "tier": "王者", "score": 9820, "accuracy": 94.2},
            {"rank": 2, "name": "DeducePro", "tier": "钻石", "score": 8760, "accuracy": 91.7},
            {"rank": 3, "name": nickname, "tier": tier, "score": total_correct * 10, "accuracy": correct_rate},
        ],
        "radar": radar,
    }


def current_user(request):
    return request.user if request.user.is_authenticated else None


@api_view(["GET"])
def health(_request):
    return Response({"status": "ok", "service": "gxlogic-bank-backend"})


@api_view(["GET"])
def dashboard(request):
    return Response(build_dashboard(current_user(request)))


@api_view(["POST"])
def generate_paper(request):
    serializer = GeneratePaperSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = int(serializer.validated_data["amount"])
    repeated = (QUESTIONS * ((amount // len(QUESTIONS)) + 1))[:amount]
    return Response({"paper": repeated})


@api_view(["POST"])
def submit_exam(request):
    serializer = SubmitExamSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    answers = serializer.validated_data.get("answers", {})

    correct = sum(1 for question in QUESTIONS if answers.get(str(question["id"])) == question["answer"])
    score = round(correct / len(QUESTIONS) * 100)

    user = current_user(request)
    progress = None
    rate = None
    event = ""
    if user is not None:
        with transaction.atomic():
            for question in QUESTIONS:
                stat, _ = TypeStat.objects.get_or_create(user=user, question_type=question["type"])
                stat.answered += 1
                if answers.get(str(question["id"])) == question["answer"]:
                    stat.correct += 1
                stat.save(update_fields=["answered", "correct"])
            ExamRecord.objects.create(user=user, total=len(QUESTIONS), correct=correct)
            progress, _ = UserProgress.objects.get_or_create(user=user)
            rate, event = settle_tier(progress)

    return Response(
        {
            "score": score,
            "tier": progress.tier if progress else None,
            "tier_event": event,
            "recent_rate": rate,
            "rank_hint": rank_hint_for(progress, rate, event),
            "analysis": [
                f"{question['type']}·{question['knowledge']}："
                f"{'答对' if answers.get(str(question['id'])) == question['answer'] else '答错'}"
                for question in QUESTIONS
            ],
        }
    )


@api_view(["POST"])
def demo_login(_request):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    user.set_password("demo1234")
    user.save(update_fields=["password"])
    refresh = RefreshToken.for_user(user)
    return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
