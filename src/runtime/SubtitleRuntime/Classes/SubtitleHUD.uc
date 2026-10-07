// 字幕专用层：其他消息继续由原始 MainHUD 绘制。
class SubtitleHUD expands MainHUD;

var CaptionState Captions;
var localized string IntroText;
var localized string CueText[16];
var float CueBegin[16];
var float CueEnd[16];
var int CueCount;
var Font SubtitleFont;
var localized string MessageSource[32];
var localized string MessageTarget[32];
var int MessageCount;

simulated function LoadCaptionText()
{
    local int i;
    IntroText=Localize("SubtitleHUD","IntroText","SubtitleRuntime",true);
    for (i=0; i<CueCount; i++)
        CueText[i]=Localize("SubtitleHUD","CueText[" $ i $ "]","SubtitleRuntime",true);
    for (i=0; i<MessageCount; i++)
    {
        MessageSource[i]=Localize("SubtitleHUD","MessageSource[" $ i $ "]","SubtitleRuntime",true);
        MessageTarget[i]=Localize("SubtitleHUD","MessageTarget[" $ i $ "]","SubtitleRuntime",true);
    }
}

simulated function string TranslateMessage(string Message)
{
    local int i;
    if (MessageCount > 0 && MessageSource[0] == "") LoadCaptionText();
    for (i=0; i<MessageCount; i++)
        if (Message == MessageSource[i]) return MessageTarget[i];
    return Message;
}

simulated function AddHandMessage(string Message, optional float Duration)
{
    Super.AddHandMessage(TranslateMessage(Message), Duration);
}

simulated function AddLeftMessage(string Message, optional float Duration)
{
    Super.AddLeftMessage(TranslateMessage(Message), Duration);
}

simulated function AddRightMessage(string Message, optional float Duration)
{
    Super.AddRightMessage(TranslateMessage(Message), Duration);
}

simulated function AddCenterMessage(string Message, optional float Duration, optional bool bEcho)
{
    Super.AddCenterMessage(TranslateMessage(Message), Duration, bEcho);
}

simulated event PostBeginPlay()
{
    Super.PostBeginPlay();
    LoadCaptionText();
}

simulated function EnsureCaptionState()
{
    local CaptionState State;
    if (Captions != None && !Captions.bDeleteMe) return;
    foreach AllActors(class'CaptionState', State)
    {
        if (State.Owner == Owner)
        {
            Captions = State;
            return;
        }
    }
    Captions = Spawn(class'CaptionState', Owner);
}

simulated function AddCaption(string Message, float Begin, float End)
{
    EnsureCaptionState();
    if (Captions != None) Captions.AddCaption(Message, Begin, End);
}

simulated function AddSubtitleMessage(string Message, optional float Duration, optional bool bEcho)
{
    local int i;
    while (Len(Message)>0 && Right(Message,1)==" ") Message=Left(Message,Len(Message)-1);
    if (Message == "") return;
    if (IntroText == "") LoadCaptionText();
    if (IntroText != "" && Left(Message, Len(IntroText)) == IntroText)
    {
        for (i=0; i<CueCount; i++)
            AddCaption(CueText[i], Level.TimeSeconds + CueBegin[i], Level.TimeSeconds + CueEnd[i]);
    }
    else
    {
        if (Duration <= 0) Duration = SubtitleMessageDuration;
        AddCaption(Message, Level.TimeSeconds, Level.TimeSeconds + Duration);
    }
    if (bEcho && PlayerPawn(Owner) != None)
        PlayerPawn(Owner).Player.Console.Message(None, Message, 'Message');
}

simulated function DrawMessages(Canvas C, float DeltaTime)
{
    local int i, j, LastOrder, BestOrder, BestIndex;
    local float X, Y, LineX, LineY, LineHeight, OldOrgX, OldOrgY, OldClipX, OldClipY;
    local Font OldFont;
    local bool OldCenter;
    local byte OldStyle;
    local color OldColor;

    // 原字幕单槽保持空，手部、中心、通用提示沿用原始路径和字号。
    SubtitleMessage.LifeSpan = 0;
    Super.DrawMessages(C, DeltaTime);
    if (SubtitleMessageIntensity == 0) return;
    if (SubtitleFont == None)
        SubtitleFont = Font(DynamicLoadObject("WOT.SubtitleFont", class'Font'));
    if (SubtitleFont == None) return;
    OldFont=C.Font; OldCenter=C.bCenter; OldStyle=C.Style; OldColor=C.DrawColor;
    OldOrgX=C.OrgX; OldOrgY=C.OrgY; OldClipX=C.ClipX; OldClipY=C.ClipY;
    EnsureCaptionState();
    if (Captions == None) return;
    C.SetFont(SubtitleFont);
    C.Style=ERenderStyle.STY_Translucent;
    C.DrawColor.R=SubtitleMessageIntensity;
    C.DrawColor.G=SubtitleMessageIntensity;
    C.DrawColor.B=SubtitleMessageIntensity;
    C.OrgX=C.SizeX/10; C.ClipX=8*C.SizeX/10;
    C.OrgY=24; C.ClipY=C.SizeY-48;
    C.StrLen("X", LineX, LineHeight);
    Y=0; LastOrder=-1;
    // 按触发顺序垂直堆叠活动字幕，各自到期，不互相替换。
    for (j=0; j<64; j++)
    {
        BestIndex=-1; BestOrder=2147483647;
        for (i=0; i<64; i++)
        {
            if (Captions.GetBegin(i) <= Level.TimeSeconds && Captions.GetEnd(i) > Level.TimeSeconds
                && !Captions.IsDuplicate(i) && Captions.GetOrder(i) > LastOrder && Captions.GetOrder(i) < BestOrder)
            {
                BestIndex=i; BestOrder=Captions.GetOrder(i);
            }
        }
        if (BestIndex<0) break;
        LastOrder=BestOrder;
        C.SetPos(0, Y);
        C.StrLen(Captions.GetText(BestIndex), X, LineY);
        C.bCenter=(LineY <= LineHeight);
        C.DrawText(Captions.GetText(BestIndex), false);
        Y += FMax(LineY,LineHeight) + 6;
    }
    C.OrgX=OldOrgX; C.OrgY=OldOrgY; C.ClipX=OldClipX; C.ClipY=OldClipY;
    C.Font=OldFont; C.bCenter=OldCenter; C.Style=OldStyle; C.DrawColor=OldColor;
    C.SetPos(0,0);
}
