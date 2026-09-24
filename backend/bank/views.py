from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from bank.models import ExamRecord, TypeStat, UserProfile
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

QUESTION_TYPES = ["数字推理", "图形推理", "逻辑判断", "类比推理", "演绎推理"]
RADAR_AXES = {
    "数字推理": "数字",
    "图形推理": "图形",
    "逻辑判断": "逻辑",
    "类比推理": "类比",
    "演绎推理": "演绎",
}

# 段位门槛：达到该段位所需的最近五套总正确率（%）
TIER_ORDER = ["青铜", "白银", "黄金", "铂金", "钻石", "王者"]
TIER_THRESHOLDS = {"青铜": 0, "白银": 60, "黄金": 70, "铂金": 80, "钻石": 88, "王者": 95}
RECENT_PAPER_LIMIT = 5


def recent_accuracy(user) -> float | None:
    """最近五套练习的总正确率，没有交卷记录时返回 None。"""
    records = ExamRecord.objects.filter(user=user)[:RECENT_PAPER_LIMIT]
    total = sum(record.total for record in records)
    if not total:
        return None
    correct = sum(record.correct for record in records)
    return correct / total * 100


def settle_tier(profile: UserProfile) -> dict:
    """按最近五套总正确率结算段位：到门槛当场晋级；低于门槛先保护一次，再低才掉段。"""
    accuracy = recent_accuracy(profile.user)
    if accuracy is None:
        return {"event": None, "accuracy": None}

    index = TIER_ORDER.index(profile.tier)
    event = None

    # 到门槛就当场晋级，允许一次连升多段
    while index + 1 < len(TIER_ORDER) and accuracy >= TIER_THRESHOLDS[TIER_ORDER[index + 1]]:
        index += 1
        event = "promoted"
    if event == "promoted":
        profile.tier = TIER_ORDER[index]
        profile.demotion_protected = False
    elif accuracy < TIER_THRESHOLDS[profile.tier]:
        if profile.demotion_protected:
            # 保护已用过，再次低于门槛才掉段
            profile.tier = TIER_ORDER[index - 1]
            profile.demotion_protected = False
            event = "demoted"
        else:
            # 第一次低于门槛，先保护一次
            profile.demotion_protected = True
            event = "protected"
    else:
        profile.demotion_protected = False

    profile.save(update_fields=["tier", "demotion_protected"])
    return {"event": event, "accuracy": round(accuracy, 1)}


def build_dashboard(user) -> dict:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    stats = {stat.question_type: stat for stat in TypeStat.objects.filter(user=user)}

    categories = []
    radar = []
    total_answered = 0
    total_correct = 0
    for index, question_type in enumerate(QUESTION_TYPES, start=1):
        stat = stats.get(question_type)
        answered = stat.answered if stat else 0
        correct = stat.correct if stat else 0
        total_answered += answered
        total_correct += correct
        # 没有作答记录的题型不计零分，雷达显示暂无数据
        accuracy = round(correct / answered * 100) if answered else None
        categories.append(
            {"id": index, "name": question_type, "accuracy": accuracy or 0, "total": answered}
        )
        radar.append({"axis": RADAR_AXES[question_type], "value": accuracy})

    return {
        "profile": {
            "nickname": user.username,
            "tier": profile.tier,
            "totalAnswered": total_answered,
            "correctRate": round(total_correct / total_answered * 100, 1) if total_answered else 0,
            "streakDays": 19,
            "practiceMinutes": 2480,
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
            {"rank": 3, "name": user.username, "tier": profile.tier, "score": 7650, "accuracy": 86.5},
        ],
        "radar": radar,
    }


@api_view(["GET"])
def health(_request):
    return Response({"status": "ok", "service": "gxlogic-bank-backend"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    return Response(build_dashboard(request.user))


@api_view(["POST"])
def generate_paper(request):
    serializer = GeneratePaperSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = int(serializer.validated_data["amount"])
    repeated = (QUESTIONS * ((amount // len(QUESTIONS)) + 1))[:amount]
    return Response({"paper": repeated})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_exam(request):
    serializer = SubmitExamSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    answers = serializer.validated_data.get("answers", {})

    # 按题型统计本次作答，并累计进账号的学习进度
    per_type: dict[str, dict[str, int]] = {}
    for question in QUESTIONS:
        bucket = per_type.setdefault(question["type"], {"answered": 0, "correct": 0})
        bucket["answered"] += 1
        if answers.get(str(question["id"])) == question["answer"]:
            bucket["correct"] += 1

    for question_type, result in per_type.items():
        stat, _ = TypeStat.objects.get_or_create(user=request.user, question_type=question_type)
        stat.answered += result["answered"]
        stat.correct += result["correct"]
        stat.save(update_fields=["answered", "correct"])

    total = sum(result["answered"] for result in per_type.values())
    correct = sum(result["correct"] for result in per_type.values())
    score = round(correct / total * 100) if total else 0
    ExamRecord.objects.create(
        user=request.user, total=total, correct=correct, accuracy=score
    )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    settlement = settle_tier(profile)
    accuracy = settlement["accuracy"]
    event = settlement["event"]
    if event == "promoted":
        rank_hint = f"最近五套总正确率 {accuracy}%，达到门槛，恭喜当场晋级{profile.tier}！"
    elif event == "protected":
        rank_hint = f"最近五套总正确率 {accuracy}%，低于{profile.tier}门槛，已触发掉段保护，再低一次将掉段。"
    elif event == "demoted":
        rank_hint = f"最近五套总正确率 {accuracy}%，再次低于门槛，段位下降至{profile.tier}。"
    else:
        rank_hint = f"最近五套总正确率 {accuracy}%，当前段位{profile.tier}，继续加油。"

    return Response(
        {
            "score": score,
            "tier": profile.tier,
            "rank_hint": rank_hint,
            "analysis": ["数字推理稳定", "图形旋转规律仍需复盘", "演绎推理建议练习充分必要条件"],
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
