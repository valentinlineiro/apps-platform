from flask import Blueprint, jsonify, request, session

import application.eligibility as eligibility_uc
import application.horizon as horizon_uc
import application.scoring as scoring_uc
from application.orcid_sync import OrcidSyncUseCase
from infrastructure.http.requests_json_client import RequestsJsonClient


def create_aneca_blueprint(journal_repo, article_repo):
    bp = Blueprint("aneca", __name__)
    _http = RequestsJsonClient()

    def _require_auth():
        if not session.get("user_id"):
            return jsonify({"error": "unauthorized"}), 401

    @bp.before_request
    def _check_auth():
        return _require_auth()

    @bp.get("/api/aneca/fields")
    def get_fields():
        return jsonify(eligibility_uc.get_fields())

    @bp.get("/api/aneca/articles")
    def get_articles():
        articles = article_repo.get_articles(session["user_id"])
        return jsonify(scoring_uc.score_articles(articles))

    @bp.put("/api/aneca/articles")
    def put_articles():
        articles = request.get_json(force=True) or []
        if not isinstance(articles, list):
            return jsonify({"error": "body must be a JSON array"}), 400
        article_repo.save_articles(session["user_id"], articles)
        return jsonify(scoring_uc.score_articles(articles))

    @bp.post("/api/aneca/orcid/sync")
    def orcid_sync():
        body = request.get_json(force=True) or {}
        orcid_id = (body.get("orcid_id") or "").strip()
        if not orcid_id:
            return jsonify({"error": "orcid_id is required"}), 400

        use_case = OrcidSyncUseCase(http_client=_http, quartile_gateway=journal_repo)
        try:
            new_articles = use_case.execute(orcid_id)
        except Exception as exc:
            return jsonify({"error": "orcid_sync_failed", "detail": str(exc)}), 502

        existing = article_repo.get_articles(session["user_id"])
        existing_titles = {a.get("titulo") for a in existing}
        merged = existing + [a for a in new_articles if a.get("titulo") not in existing_titles]
        article_repo.save_articles(session["user_id"], merged)
        return jsonify(scoring_uc.score_articles(merged))

    @bp.post("/api/aneca/score")
    def score():
        articles = request.get_json(force=True) or []
        if not isinstance(articles, list):
            return jsonify({"error": "body must be a JSON array"}), 400
        return jsonify(scoring_uc.score_articles(articles))

    @bp.post("/api/aneca/evaluate")
    def evaluate():
        body = request.get_json(force=True) or {}
        required = {"field_key", "figura", "sexenios", "horas", "docentia"}
        missing = required - body.keys()
        if missing:
            return jsonify({"error": "missing_fields", "fields": sorted(missing)}), 400

        try:
            result = eligibility_uc.evaluate(
                field_key=body["field_key"],
                figura=body["figura"],
                sexenios=int(body["sexenios"]),
                horas=int(body["horas"]),
                docentia=body["docentia"],
                expediente=body.get("expediente", []),
                sexenio_transferencia=bool(body.get("sexenio_transferencia", False)),
                patentes=int(body.get("patentes", 0)),
                spin_offs=int(body.get("spin_offs", 0)),
                contratos_art83=int(body.get("contratos_art83", 0)),
                divulgacion=bool(body.get("divulgacion", False)),
            )
        except (KeyError, ValueError) as exc:
            return jsonify({"error": "invalid_input", "detail": str(exc)}), 400

        return jsonify({
            **result,
            "action_plan": horizon_uc.build_action_plan(result["detalle"]),
            "explainability": horizon_uc.build_explainability(result["apto"], result["detalle"]),
        })

    return bp
