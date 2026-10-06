// List functions marked non-returning, with how many call sites each has.
// @category Nokia3510

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class ListNoReturn extends GhidraScript {
	@Override
	protected void run() throws Exception {
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			if (!f.hasNoReturn())
				continue;
			int calls = 0;
			for (Reference r : getReferencesTo(f.getEntryPoint()))
				if (r.getReferenceType().isCall())
					calls++;
			printf("NORETURN %s %s calls=%d\n", f.getEntryPoint(), f.getName(), calls);
		}
	}
}
