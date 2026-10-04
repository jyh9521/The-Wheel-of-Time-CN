// Compiler proof only; not installed or distributed as a game package.
class LocaleDisplayProbe expands menuLong;
var bool Flag;
var string Detail;
function string Raw() { return string(Flag); }
function string Mapped() { return GetOnOffStr(Flag); }

function string DetailMapped() { return GetLowMediumHighStr(byte(Detail == "Medium") + 2 * byte(Detail == "High")); }
