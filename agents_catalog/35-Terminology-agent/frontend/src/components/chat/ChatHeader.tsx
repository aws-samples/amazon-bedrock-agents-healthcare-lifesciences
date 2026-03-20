import { Button } from "@/components/ui/button"
import { Plus, Info } from "lucide-react"
import { useAuth } from "@/hooks/useAuth"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

type ChatHeaderProps = {
  title?: string | undefined
  onNewChat: () => void
  canStartNewChat: boolean
}

export function ChatHeader({ title, onNewChat, canStartNewChat }: ChatHeaderProps) {
  const { isAuthenticated, signOut } = useAuth()

  return (
    <header className="flex items-center justify-between p-4 border-b w-full">
      <div className="flex items-center">
        <h1 className="text-xl font-bold">{title || "Terminology Agent"}</h1>
      </div>
      <div className="flex items-center gap-2">
        <Button onClick={onNewChat} variant="outline" className="gap-2" disabled={!canStartNewChat}>
          <Plus className="h-4 w-4" />
          New Chat
        </Button>

        {/* Info Button */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="icon" title="Agent Information">
              <Info className="h-4 w-4" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-2xl">About Terminology Agent</AlertDialogTitle>
              <AlertDialogDescription className="text-left space-y-4 pt-4">
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">What is this agent?</h3>
                  <p className="text-gray-700">
                    The Terminology Agent standardizes medical and biological terminology using 200+ ontologies
                    from the EBI Ontology Lookup Service (OLS). It helps researchers, clinicians, and data scientists
                    find, map, and standardize medical terms across different coding systems.
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Key Capabilities</h3>
                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                    <li><strong>Ontology Search:</strong> MONDO, ChEBI, HPO, GO, EFO, and 200+ ontologies</li>
                    <li><strong>Entity Extraction:</strong> Automatically identify diseases, drugs, genes, proteins, anatomy</li>
                    <li><strong>Hierarchical Exploration:</strong> Find parent/child terms and relationships</li>
                    <li><strong>Multi-Ontology Mapping:</strong> Map across MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC</li>
                    <li><strong>Term Standardization:</strong> Convert variant terms to official codes</li>
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Example Queries</h3>
                  <div className="space-y-2">
                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                      <p className="text-sm font-medium text-gray-800">Basic Lookup:</p>
                      <p className="text-sm text-gray-600">"What is the MONDO ID for diabetes mellitus?"</p>
                      <p className="text-sm text-gray-600">"Find the ChEBI identifier for aspirin"</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                      <p className="text-sm font-medium text-gray-800">Hierarchical Search:</p>
                      <p className="text-sm text-gray-600">"Show me parent and child terms for myocardial infarction"</p>
                      <p className="text-sm text-gray-600">"What are the ancestors of MONDO:0005068?"</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                      <p className="text-sm font-medium text-gray-800">Multi-Ontology:</p>
                      <p className="text-sm text-gray-600">"Search for insulin across ChEBI and GO ontologies"</p>
                      <p className="text-sm text-gray-600">"Map diabetes to all relevant ontologies"</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                      <p className="text-sm font-medium text-gray-800">Entity Extraction:</p>
                      <p className="text-sm text-gray-600">"Extract entities from: Patient with diabetes on metformin"</p>
                      <p className="text-sm text-gray-600">"Standardize: heart attack, MI, myocardial infarction"</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Data Sources</h3>
                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                    <li><strong>Authoritative:</strong> EBI OLS API (real-time lookups from official ontologies)</li>
                    <li><strong>Suggestions:</strong> LLM training data (for ontologies not in OLS like MedDRA, SNOMED CT)</li>
                  </ul>
                  <p className="text-sm text-gray-600 mt-2">
                    The agent clearly indicates which source is used for each result.
                  </p>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction>Close</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {isAuthenticated && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline">Logout</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Confirm Logout</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to log out? You will need to sign in again to access your
                  account.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => signOut()}>Confirm</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>
    </header>
  )
}
