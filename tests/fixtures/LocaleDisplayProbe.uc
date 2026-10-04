// Compiler proof only; not installed or distributed as a game package.
class LocaleDisplayProbe expands menuLong;
var bool Flag;
function string Raw() { return string(Flag); }
function string Mapped() { return GetOnOffStr(Flag); }
