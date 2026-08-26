<?php
/**
 * Plugin Name: Alphababy - correctif feuille de style jQuery UI
 * Description: Retire la feuille de style jquery-ui-style pointant vers le CDN Google, qui renvoie une page d'erreur 404 HTML mise en cache par WP Rocket comme du CSS et casse la mise en page.
 * Version: 1.0.0
 * Author: SEO Monkey
 *
 * Contexte
 * --------
 * Un plugin de reservation enregistre la feuille de style « jquery-ui-style »
 * vers ajax.googleapis.com en construisant l'URL a partir de la version de
 * jQuery UI livree par WordPress :
 *
 *   //ajax.googleapis.com/ajax/libs/jqueryui/<version>/themes/smoothness/jquery-ui.css
 *
 * Le CDN Google ne publie jQuery UI que jusqu'a la 1.12.1. Avec la 1.14.2
 * livree par le coeur, l'URL renvoie la page d'erreur 404 de Google, en HTML.
 *
 * WP Rocket minifie cette reponse et la ressert depuis
 * /wp-content/cache/min/ avec l'en-tete Content-Type: text/css. Le navigateur
 * accepte alors le fichier comme une feuille de style et applique les regles
 * du bloc <style> de la page d'erreur :
 *
 *   * { margin: 0; padding: 0 }
 *   html { padding: 15px; font: 15px/22px arial }
 *   body { margin: 7% auto 0; max-width: 390px }
 *   * > body { padding-right: 205px }
 *
 * Resultat : le site entier est comprime dans une colonne de 390 px.
 *
 * La feuille renvoyant une 404, elle n'a jamais rien style. La retirer ne
 * change donc rien a l'apparence, elle supprime seulement la corruption et la
 * requete inutile. Si un theme jQuery UI devient necessaire pour le
 * calendrier de reservation, heberger le fichier en local et le rattacher au
 * meme identifiant plutot que de reintroduire une dependance CDN.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Retire la feuille de style seulement si elle pointe encore vers le CDN
 * Google. Si le plugin d'origine est corrige ou si la feuille est rebasculee
 * en local, on n'y touche pas.
 */
function alphababy_remove_broken_jquery_ui_style() {
	$styles = wp_styles();

	if ( ! isset( $styles->registered['jquery-ui-style'] ) ) {
		return;
	}

	$src = (string) $styles->registered['jquery-ui-style']->src;

	if ( false === strpos( $src, 'ajax.googleapis.com' ) ) {
		return;
	}

	wp_dequeue_style( 'jquery-ui-style' );
	wp_deregister_style( 'jquery-ui-style' );
}
add_action( 'wp_enqueue_scripts', 'alphababy_remove_broken_jquery_ui_style', 99 );
add_action( 'wp_print_styles', 'alphababy_remove_broken_jquery_ui_style', 1 );
