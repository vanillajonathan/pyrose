import os
import platform
import lsp_types as lsp


def get_initialize_params(version: str) -> lsp.InitializeParams:
    """Get LSP initialization parameters.

    Args:
      version: The client version.

    Returns:
      Initialization parameters for the LSP.
    """
    params: lsp.InitializeParams = {
        "processId": os.getpid(),
        "clientInfo": {"name": "PyRose", "version": version},
        "locale": "en",
        "rootUri": None,
        "capabilities": {
            "textDocument": {
                "completion": {
                    "completionItem": {
                        "snippetSupport": False,
                        "documentationFormat": [
                            lsp.MarkupKind.Markdown,
                            lsp.MarkupKind.PlainText,
                        ],
                        "deprecatedSupport": True,
                        "tagSupport": {"valueSet": [lsp.CompletionItemTag.Deprecated]},
                        "labelDetailsSupport": True,
                    },
                    "completionItemKind": {
                        "valueSet": [
                            lsp.CompletionItemKind.Text,
                            lsp.CompletionItemKind.Method,
                            lsp.CompletionItemKind.Function,
                            lsp.CompletionItemKind.Constructor,
                            lsp.CompletionItemKind.Field,
                            lsp.CompletionItemKind.Variable,
                            lsp.CompletionItemKind.Class,
                            lsp.CompletionItemKind.Interface,
                            lsp.CompletionItemKind.Module,
                            lsp.CompletionItemKind.Property,
                            lsp.CompletionItemKind.Unit,
                            lsp.CompletionItemKind.Value,
                            lsp.CompletionItemKind.Enum,
                            lsp.CompletionItemKind.Keyword,
                            lsp.CompletionItemKind.Snippet,
                            lsp.CompletionItemKind.Color,
                            lsp.CompletionItemKind.File,
                            lsp.CompletionItemKind.Reference,
                            lsp.CompletionItemKind.Folder,
                            lsp.CompletionItemKind.EnumMember,
                            lsp.CompletionItemKind.Constant,
                            lsp.CompletionItemKind.Struct,
                            lsp.CompletionItemKind.Event,
                            lsp.CompletionItemKind.Operator,
                            lsp.CompletionItemKind.TypeParameter,
                        ]
                    },
                    # "contextSupport": True
                },
                "hover": {
                    "contentFormat": [lsp.MarkupKind.Markdown, lsp.MarkupKind.PlainText]
                },
                "publishDiagnostics": {
                    "tagSupport": {
                        "valueSet": [
                            lsp.DiagnosticTag.Unnecessary,
                            lsp.DiagnosticTag.Deprecated,
                        ]
                    }
                },
            },
            "general": {
                "regularExpressions": {
                    "engine": "Python",
                    "version": platform.python_version(),
                },
                "positionEncodings": [lsp.PositionEncodingKind.UTF8],
            },
        },
        "trace": lsp.TraceValue.Off,
    }

    return params
